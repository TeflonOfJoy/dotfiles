#ifndef contact_h
#define contact_h


typedef struct contact Contact, *ContactPtr;
/**
* Nota: useremo solo puntatori a Contact, e chiameremo per semplicità "contatto" un puntatore a Contact  
*/

/**
* @brief Crea un nuovo contatto 
*
* @param name La stringa che contiene il nome 
* @param surname La stringa che contiene il cognome 
* @param mobile La stringa che contiene il numero di cellulare 
* @param url La stringa che contiene la home page  
* @return Il puntatore alla struttura che rappresenta il contatto, NULL se ((name == NULL) || (surname == NULL))
*/
ContactPtr mkContact(char* name, char* surname, char* mobile, char* url);

/**
* @brief Dealloca una struttura Contact e mette il relativo puntatore (che dunque deve essere passato per riferimento) a NULL
*
* @param cntptr il puntatore al contatto (non può essere NULL). Nota: cntptr è un puntatore a puntatore a Contact
*/
void dsContact(ContactPtr* cntptr);

/**
* @brief Aggiorna il telefono di un contatto 
*
* @param cnt Il contatto 
* @param mobile La stringa che contiene il nuovo numero di cellulare  (può essere NULL)
*/
void updateMobile(ContactPtr cnt, char* newMobile);

/**
* @brief Aggiorna la home page di un contatto 
*
* @param cnt Il contatto 
* @param url La stringa che contiene la nuova home page  (può essere NULL)
*/
void updateUrl(ContactPtr cnt, char* newUrl);

/**
* @brief Restituisce il nome di un contatto 
*
* @param cnt Il contatto 
* @return url La stringa che contiene il nome del contatto 
*/
char* getName(const ContactPtr cnt);

/**
* @brief Restituisce il cognome di un contatto 
*
* @param cnt Il contatto 
* @return url La stringa che contiene il cognome del contatto 
*/
char* getSurname(const ContactPtr cnt);

/**
* @brief Restituisce il numero di cellulare di un contatto 
*
* @param cnt Il contatto 
* @return url La stringa che contiene il numero di cellulare  (può essere NULL)
*/
char* getMobile(const ContactPtr cnt);

/**
* @brief Restituisce la home page di un contatto 
*
* @param cnt Il contatto 
* @return url La stringa che contiene la nuova home page  (può essere NULL)
*/
char* getUrl(const ContactPtr cnt);

/**
* @brief Controlla se due contatti sono uguali rispetto al cognome e al nome
* 
* @param cnt1 Il primo contatto
* @param cnt2 Il secondo contatto 
* @return 1 se i due contatti hanno lo stesso cognome e lo stesso nome, 0 altrimenti 
*/
_Bool equalsContact(const ContactPtr cnt1, const ContactPtr cnt2);

/**
* @brief Confronta due contatti in ordine lessicografico in base al cognome e al nome
*
* @param cnt1 Il primo contatto 
* @param cnt2 Il secondo contatto 
* @return -1 se cnt1 minore cnt2, 0 se cnt1 uguale cnt2, 1 se cnt1 maggiore cnt2
*/
int cmpContact(const ContactPtr cnt1, const ContactPtr cnt2);

#endif
