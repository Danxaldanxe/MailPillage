# MailPillage
python code to connect to mail servers and pillage the data contained within

Sample Usage:


To simple check if creds are valid:

./mailpillager.py -s <server ip/fqdn> -t <server type> -u <username> -d <domain name> -p "<password>"


To search for interecting messages/attachments based on search terms:

./mailpillager.py -s <server ip/fqdn> -t <server type> -u <username> -d <domain name> -p "<password>" --searchstring "<search terms>"


To download identified emails:

./mailpillager.py -s <server ip/fqdn> -t <server type> -u <username> -d <domain name> -p "<password>" --searchstring "<search terms>" --emails


To download identified attachments (currently the ews module does not download attachments):

./mailpillager.py -s <server ip/fqdn> -t <server type> -u <username> -d <domain name> -p "<password>" --searchstring "<search terms>" --attachments


To print constructed contact list: 

./mailpillager.py -s <server ip/fqdn> -t <server type> -u <username> -d <domain name> -p "<password>" --contacts
