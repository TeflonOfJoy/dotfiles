// ==UserScript==
// @name         vitalsource-fetch
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Decrypt and create EPUB/PDF from books on vitalsource
// @license      MIT
// @match        *://*.com/reader/books/*
// @match        https://jigsaw.vitalsource.com/books/*
// @grant        GM.xmlHttpRequest
// @require      https://unpkg.com/epub-gen-memory@1.0.10/dist/bundle.min.js
// ==/UserScript==

(function () {
    'use strict';

    async function decryptAndCreateEPUB(encryptionKeyBuffer) {
        // progress overlay
        const overlay = document.createElement('div');
        overlay.style.position = 'fixed';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        overlay.style.color = 'white';
        overlay.style.zIndex = '10000';
        overlay.style.display = 'flex';
        overlay.style.flexDirection = 'column';
        overlay.style.alignItems = 'center';
        overlay.style.justifyContent = 'center';
        overlay.innerHTML = `
        <h1>Creating EPUB...</h1>
        <p id="progress-text-jihughk">Initializing...</p>
        <progress id="progress-bar-jihughk" value="0" max="100"></progress>
      `;
        document.body.appendChild(overlay);

        function updateProgress(text, value) {
            document.getElementById('progress-text-jihughk').textContent = text;
            document.getElementById('progress-bar-jihughk').value = value;
        }

        function selfDestruct() {
            overlay.innerHTML = `
          <h1>Error occurred</h1>
          <p>Script self-destructed.</p>
        `;
            setTimeout(() => {
                overlay.remove();
            }, 3000);
        }

        function getCrypto() {
            return window.crypto || window.msCrypto;
        }

        function importSecretKey(keyBuffer) {
            return getCrypto().subtle.importKey('raw', keyBuffer, 'AES-GCM', true, ['encrypt', 'decrypt']);
        }

        function base64ToArrayBuffer(base64) {
            var binaryString = atob(base64);
            var len = binaryString.length;
            var bytes = new Uint8Array(len);
            for (var i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            return bytes.buffer;
        }

        function arrayBufferToString(buffer) {
            if ('TextDecoder' in window) {
                return new TextDecoder('utf-16').decode(buffer);
            }
            var str = '';
            for (var i = 0; i < buffer.byteLength; i += 2) {
                str += String.fromCharCode.apply(null, new Uint16Array(buffer.slice(i, i + 2)));
            }
            return str;
        }

        // function getTag(data, tagLength = 128) {
        //   var tagOffset = data.byteLength - ((tagLength + 7) >> 3);
        //   return data.slice(tagOffset);
        // }

        // function getTaglessText(data, tagLength = 128) {
        //   var tagOffset = data.byteLength - ((tagLength + 7) >> 3);
        //   return data.slice(0, tagOffset);
        // }

        function decryptMessage(key, encryptedData, iv) {
            return getCrypto().subtle.decrypt(
                {
                    iv: iv,
                    name: 'AES-GCM',
                    tagLength: 128,
                },
                key,
                encryptedData
            );
        }

        function toPromiseOrNotToPromise(promise, callback) {
            if (promise.then) {
                promise.then(callback).catch(
                    (err) => {
                        console.error(err);
                        selfDestruct();
                    }
                );
            } else {
                promise.oncomplete = function (event) {
                    callback(event.target.result);
                };
            }
        }

        async function extractBookNumberWithRetry(retries = 10, delay = 10000) {
            const regex = /books\/(\d+)\//;
            for (let attempt = 1; attempt <= retries; attempt++) {
                const match = window.location.href.match(regex);
                if (match) {
                    return match[1];
                } else {
                    await sleep(delay);
                }
            }
            throw new Error('Book number not found in URL after multiple attempts.');
        }

        function sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }

        function httpRequest(method, url, callback) {
            GM.xmlHttpRequest({
                method: method,
                url: url,
                onload: function (response) {
                    if (response.status === 200) {
                        callback(response.responseText);
                    } else {
                        selfDestruct();
                    }
                },
                onerror: function (error) {
                    console.error('Request error:', error);
                    selfDestruct();
                }
            });
        }

        function getPageContent(url) {
            return new Promise((resolve, reject) => {
                GM.xmlHttpRequest({
                    method: "GET",
                    url: url,
                    onload: function (response) {
                        if (response.status === 200) {
                            resolve(response.responseText);
                        } else {
                            reject(new Error(`Failed to load page content: ${response.status}`));
                        }
                    },
                    onerror: function (error) {
                        reject(new Error(`Request error: ${JSON.stringify(error)}`));
                    }
                });
            });
        }

        async function parsePageContentWithRetry(htmlContent, retries = 2) {
            const parser = new DOMParser();
            const doc = parser.parseFromString(htmlContent, 'text/html');
            for (let attempt = 1; attempt <= retries; attempt++) {
                const pageContentElement = doc.getElementById('page-content');
                if (pageContentElement) {
                    return pageContentElement.textContent;
                } else {
                    if (attempt < retries) {
                        console.warn('Page content element not found, retrying...');
                        await sleep(2000);
                    }
                }
            }
            console.error('Page content element not found after multiple attempts, skipping page.');
            return null;
        }

        function extractCssFilename(doc) {
            const linkElement = doc.querySelector('link[rel="stylesheet"]');
            if (linkElement) {
                const href = linkElement.getAttribute('href');
                const cssFilename = href;
                return cssFilename;
            } else {
                return null;
            }
        }

        function replaceRelativeUrls(doc, bookNumber) {
            const imgElements = doc.querySelectorAll('img');
            imgElements.forEach(img => {
                const src = img.getAttribute('src');
                if (src && !src.startsWith('http') && !src.startsWith('https')) {
                    img.setAttribute('src', `https://jigsaw.vitalsource.com/books/${bookNumber}/epub/OEBPS/${src.replace("../", "")}`);
                }
            });

            const linkElements = doc.querySelectorAll('link[rel="stylesheet"]');
            linkElements.forEach(link => {
                const href = link.getAttribute('href');
                if (href && !href.startsWith('http') && !href.startsWith('https')) {
                    link.setAttribute('href', `https://jigsaw.vitalsource.com/books/${bookNumber}/epub/OEBPS/${href.replace("../", "")}`);
                }
            });
        }

        function b64DecodeUnicode(str) {
            return decodeURIComponent(atob(str).split('').map(function (c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));
        }

        async function fetchResource(url, retries = 3) {
            for (let attempt = 1; attempt <= retries; attempt++) {
                try {
                    return new Promise((resolve, reject) => {
                        GM.xmlHttpRequest({
                            method: "GET",
                            url: url,
                            responseType: "blob",
                            onload: function (response) {
                                if (response.status === 200) {
                                    resolve(response.response);
                                } else {
                                    reject(new Error(`Failed to load resource: ${response.status}`));
                                }
                            },
                            onerror: function (error) {
                                reject(new Error(`Request error: ${JSON.stringify(error)}`));
                            }
                        });
                    });
                } catch (error) {
                    if (attempt < retries) {
                        await sleep(2000);
                    } else {
                        throw error;
                    }
                }
            }
        }

        async function fetchTextResource(url, retries = 3) {
            for (let attempt = 1; attempt <= retries; attempt++) {
                try {
                    return new Promise((resolve, reject) => {
                        GM.xmlHttpRequest({
                            method: "GET",
                            url: url,
                            onload: function (response) {
                                if (response.status === 200) {
                                    resolve(response.responseText);
                                } else {
                                    reject(new Error(`Failed to load text resource: ${response.status}`));
                                }
                            },
                            onerror: function (error) {
                                reject(new Error(`Request error: ${JSON.stringify(error)}`));
                            }
                        });
                    });
                } catch (error) {
                    if (attempt < retries) {
                        await sleep(2000);
                    } else {
                        throw error;
                    }
                }
            }
        }

        async function fetchBookInfo(bookNumber) {
            return new Promise((resolve, reject) => {
                const url = `https://jigsaw.vitalsource.com/info/books.json?isbns=${bookNumber}`;
                httpRequest('GET', url, (response) => {
                    try {
                        const bookInfo = JSON.parse(response).books[0];
                        resolve(bookInfo);
                    } catch (error) {
                        reject(error);
                    }
                });
            });
        }

        async function createEPUB(bookInfo, bookNumber, pagesJson, secretKey) {
            const chapters = [];
            let cssText = null;

            const fetchMedia = async (url) => {
                const blob = await fetchResource(url);
                const filename = url.split('/').pop();
                return { filename, blob };
            };

            // hidden div to render HTML content (bad idea)
            // const hiddenDiv = document.createElement('div');
            // hiddenDiv.style.display = 'none';
            // document.body.appendChild(hiddenDiv);

            for (let i = 0; i < pagesJson.length; i++) {
                let page = pagesJson[i];
                updateProgress(`Processing page ${i + 1} of ${pagesJson.length}`, ((i + 1) / pagesJson.length) * 100);

                if (page.absoluteURL) {
                    const pageContentHtml = await getPageContent("https://jigsaw.vitalsource.com" + page.absoluteURL);
                    const pageContent = await parsePageContentWithRetry(pageContentHtml);
                    if (pageContent) {
                        const contentParts = pageContent.split(':');
                        const iv = new Uint8Array(contentParts[0].split(','));
                        const encryptedData = base64ToArrayBuffer(contentParts[1]);
                        const decryptedPromise = decryptMessage(secretKey, encryptedData, iv);
                        await new Promise(resolve => {
                            toPromiseOrNotToPromise(decryptedPromise, async function (decryptedBuffer) {
                                const decryptedMessage = arrayBufferToString(decryptedBuffer);
                                const decodedMessage = b64DecodeUnicode(decryptedMessage);
                                const parser = new DOMParser();
                                const doc = parser.parseFromString(decodedMessage, 'application/xhtml+xml');

                                // Remove all <script> and <iframe> elements
                                // const scripts = doc.querySelectorAll('script, iframe');
                                // scripts.forEach(script => script.remove());

                                // Remove `body{visibility:hidden !important;}` from the style tag
                                // const styles = doc.querySelectorAll('style');
                                // styles.forEach(style => {
                                //   style.innerHTML = style.innerHTML.replace(/body\s*\{\s*visibility\s*:\s*hidden\s*!important\s*;\s*\}/g, '');
                                // });

                                // relative URLs to absolute
                                replaceRelativeUrls(doc, bookNumber);

                                if (!cssText) {
                                    const cssFilename = extractCssFilename(doc);
                                    if (cssFilename) {
                                        cssText = await fetchTextResource(cssFilename);
                                    }
                                }

                                // Append content to hidden div to render it (terrible)
                                // hiddenDiv.innerHTML = new XMLSerializer().serializeToString(doc);
                                // const renderedHTML = hiddenDiv.innerHTML;

                                chapters.push({
                                    content: new XMLSerializer().serializeToString(doc),
                                    excludeFromToc: true,
                                });
                                resolve();
                            });
                        });
                    }
                    await sleep(2000);
                }
            }

            const options = {
                title: bookInfo.title,
                author: bookInfo.author,
                publisher: bookInfo.publisher || 'anonymous',
                description: bookInfo.description || '',
                cover: `https:${bookInfo.coverURL}.jpeg`,
                tocTitle: "",
                tocInTOC: false,
                numberChaptersInTOC: false,
                prependChapterTitles: false,
                date: bookInfo.builtAt || new Date().toISOString().split('T')[0],
                lang: "en",
                css: cssText || '',
                version: 3,
                ignoreFailedDownloads: true,
                verbose: true
            };

            console.log(`https:${bookInfo.coverURL.replace(':width', '200')}`)

            updateProgress('Generating EPUB file...', 100);
            const epub = await new window.epubGen.EPub(options, chapters).render();
            epub.generateAsync({ type: 'blob' }).then((epubBlob) => {
                const blobUrl = URL.createObjectURL(epubBlob);
                const a = document.createElement('a');
                a.href = blobUrl;
                a.download = `${bookNumber}.epub`;
                a.click();
                // hiddenDiv.remove();
                overlay.remove();
            }).catch((err) => {
                selfDestruct();
            });
        }

        // main
        try {
            const bookNumber = await extractBookNumberWithRetry();
            const bookInfo = await fetchBookInfo(bookNumber);

            const targetUrl = `https://jigsaw.vitalsource.com/books/${bookNumber}/epub/OEBPS/dummy/1`;

            while (window.location.href != targetUrl) {
                if (window.location.href.includes("epubcfi")) {
                    window.location.href = targetUrl;
                }
                await sleep(2000);
            }

            httpRequest('GET', `https://jigsaw.vitalsource.com/books/${bookNumber}/pages`, async function (response) {
                const pagesJson = JSON.parse(response);
                const secretKey = await importSecretKey(encryptionKeyBuffer);
                await createEPUB(bookInfo, bookNumber, pagesJson, secretKey);
            });

        } catch (error) {
            selfDestruct();
        }
    }

    var encryptionKeyBuffer = new Uint8Array([
        220, 109, 186, 84, 172, 145, 201, 231, 86, 164, 221, 52, 209, 62, 69, 178,
        216, 96, 128, 108, 45, 47, 246, 172, 38, 254, 252, 79, 172, 113, 212, 194,
    ]);

    decryptAndCreateEPUB(encryptionKeyBuffer);
})();