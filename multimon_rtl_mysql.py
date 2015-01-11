#!/usr/bin/python
# -*- coding: cp1252 -*-
'''
!! This requires a recent build of Multimon-NG as the old builds wont accept a piped input !!
Change the rtl_fm string to suit your needs.. add -a POCSAG512 , 2400 etc if needed to the Multimon-ng string
This just prints and writes to a file, you can put it in a threaded class and pass though a queue
or whatever suits your needs.

Aenderungen  fuer Deutschland und Kommentare von Smith - Funkmeldesystem.de-Forum.
Bitte beachten, bei POC512 ist die Zeichenkette jeweiles um ein Zeichen kuerzer!
MySQL-Funktion hinzugefuegt. 

Pyton MySQL-Support installieren
wget "http://dev.mysql.com/get/Downloads/Connector-Python/mysql-connector-python-1.0.9.tar.gz/from/http://cdn.mysql.com/" -O mysql-connector.tar && tar xfv mysql-connector.tar && cd mysql-connector-python* && chmod +x ./setup.py && sudo ./setup.py install

'''
import time
import sys
import subprocess
import os
import mysql
import mysql.connector

########################################
##### Hier die Userdaten eintragen ##### 
########################################
dbserver = "localhost"
dbuser = ""
dbpassword = ""
datenbank = ""
TabellePOC = "ras_pocsag_hist"
TabelleFMS = "ras_fms_hist"
TabelleZVEI = "ras_zvei_hist"

# Kanal = ((Frequenz - 84,015 MHz) / 0,02 MHz) + 347 des Oberbandes 4m
# Vor den Kanal ein O fuer Oberband - ein U fuer Unterband. Es werden nur die technischen Kanaele 101-125 im 2m Band beruecksichtigt!
kanal = "OXXX"

# Fehlerkorrektur ppm DVB-T Stick
ppmerror = "31"

# DVB-T Stick Device ID, Testen mit "rtl_test"
deviceid = "0"

# -a POCSAG512 -a POCSAG1200 -a POCSAG2400 -a FMSFSK -a ZVEI2
demod1 = ""
demod2 = ""
demod3 = ""

########################################
##### Userdaten ENDE               ##### 
########################################
a_schleife_zvei = ""
a_address_fms = ""
a_status_fms = ""
a_richtung_fms = ""
a_zeit_zvei = int(time.time())
a_zeit_fms = int(time.time())
frequenz = "0"
if kanal[0:2] == "U1":
   frequenz = ((int(kanal[1:4]) - 101) * 0.02) + 165.210
elif kanal[0:2] == "O1":
   frequenz = ((int(kanal[1:4]) - 101) * 0.02) + 169.810
elif kanal[0:1] == "O":
   frequenz = ((int(kanal[1:4]) - 347) * 0.02) + 84.015
elif kanal[0:1] == "U":
   frequenz = ((int(kanal[1:4]) - 347) * 0.02) + 74.215
else:
   frequenz = "1"
print "eingestellter Kanal: " + kanal[1:4] + " " + kanal[0] + "B"
print "Kanalfrequenz: " + str(frequenz) + " MHz"
# ZVEI Filter Schleifen
zvei_filter = ['00000', '11111', '22222', '33333', '44444', '55555', '66666', '77777', '88888', '99999']
try:
    connection = mysql.connector.connect(host = str(dbserver), user = str(dbuser), passwd = str(dbpassword), db = str(datenbank))
except:
    print "Keine Verbindung zum Server"
    exit(0)
def curtime():
    return time.strftime("%Y-%m-%d %H:%M:%S")
with open('Fehler.txt','a') as file:
    file.write(('#' * 20) + '\n' + curtime() + '\n')
multimon_ng = subprocess.Popen("rtl_fm -d "+str(deviceid)+" -f "+str(frequenz)+"M -M fm -s 22050 -p "+str(ppmerror)+" -E DC -F 0 -g 100 | multimon-ng "+str(demod1)+" "+str(demod2)+" "+str(demod3)+" -f alpha -t raw -",
                               #stdin=rtl_fm.stdout,
                               stdout=subprocess.PIPE,
                               stderr=open('error_marcel.txt','a'),
                               shell=True)
try:
    while True:
        line = multimon_ng.stdout.readline()
        multimon_ng.poll()
        with open('Line.txt','a') as a:
            a.write(line)
         # ZVEI - Abfrage
        if line.startswith('ZVEI2'):
            address = line[7:12].replace(" ", "")
            address = address.replace("\n","")
            address = address.replace("\r","")
            if len(address) == 5:
                   ### Schleifen filtern 00000, 11111, ... ###	
                   if address == any(zvei_filter) :
                       print address + " - ZVEI ausgefiltert - nichts unternommen"
                 ### Schleifen filtern /ENDE ###         
                   else:
                        utc_stamp = int(time.time())
                        # Wiederholton 'F' auflösen
                        s1 = address[0]
                        s2 = address[1]
                        s3 = address[2]
                        s4 = address[3]
                        s5 = address[4]
                        if s2 == "F":
                            s2 = s1
                        if s3 == "F":
                            s3 = s2
                        if s4 == "F":
                            s4 = s3
                        if s5 == "F":
                            s5 = s4
                        address2 = s1 + s2 + s3 + s4 + s5
                        # Pruefen ob Schleife numerisch ist
                        if address2.isdigit() is True:
                            # Pruefen auf Doppelalarmierung
                            if address2 == a_schleife_zvei and utc_stamp < a_zeit_zvei + 10:
                                print address2 + " - ZVEI Doppelalarmierung - nichts unternommen"
                            else:
                                output=(curtime()+' '+ address2+'\n')
                                print curtime(), address2
                                with open('ZVEI.txt','a') as f:                                           
                                            f.write(output)
                                cursor = connection.cursor()
                                cursor.execute("INSERT INTO "+str(TabelleZVEI)+" (time,schleife,kanal) VALUES (%s,%s,%s)",(curtime(),address2,kanal,))
                                cursor.close()
                                connection.commit()
                        else:
                            print address + " - ZVEI nicht numerisch - nichts unternommen"
                        a_zeit_zvei = utc_stamp
                        a_schleife_zvei = address2
            else:
                print address + " - ZVEI nicht vollstaendig - nichts unternommen"
                
        # FMS - Abfrage
        elif line.startswith('FMS'):
            utc_stamp = int(time.time())		
            bos = line[19]
            land = line[36]
            kreis= line[65:67]
            fhzg = line[72:76]
            status = line[84]
            status = status.replace("\n","")
            status = status.replace("\r","")
            richtung = line[101]
            richtung = richtung.replace("\n","")
            richtung = richtung.replace("\r","")
            address = (bos+''+ land+''+ kreis+''+ fhzg)
            # Pruefen auf Doppelstatus
            if address == a_address_fms and status == a_status_fms and richtung == a_richtung_fms and utc_stamp < a_zeit_fms + 3:
                print address + ", Status: " + status + ", Richtung: " + richtung + " - FMS Doppelstatus - nichts unternommen"
            else:
                output= (curtime()+' '+ bos+''+ land+''+ kreis+''+ fhzg+' '+status+' '+richtung+'\n')
                # Pruefen ob FMS Telegram vollstaendig ist	
                if address != "" and status != "" and richtung != "":
                    # Nur Fahrzeug --> Leitstelle (0) in DB schreiben
                    if richtung == "0":
                        print curtime(), address, status, richtung
                        with open('FMS.txt','a') as f:                                           
                           f.write(output)
                        cursor = connection.cursor()
                        cursor.execute("INSERT INTO "+str(TabelleFMS)+" (timestamp,kennung,status,richtung,kanal) VALUES (%s,%s,%s,%s,%s)",(curtime(),address,status,richtung,kanal,))
                        cursor.close()
                        connection.commit()
                    else:
                        print address + ", Status: " + status + ", Richtung: " + richtung + " - FMS falsche Richtung - nichts unternommen"	
                else:
                    print address + ", Status: " + status + ", Richtung: " + richtung + " - FMS nicht vollstaendig - nichts unternommen"
            a_zeit_fms = utc_stamp
            a_address_fms = address
            a_status_fms = status
            a_richtung_fms = richtung	
        # POCSAG - Abfrage
        elif line.__contains__("Alpha:"):
            if line.startswith('POCSAG'):
                utc_stamp = int(time.time())	
                address = line[21:28].replace(" ", "").zfill(7)	                        
                subric = line[40:41].replace(" ", "").replace("3", "4").replace("2", "3").replace("1", "2").replace("0", "1")
                message = line.split('Alpha:   ')[1].strip().rstrip('<EOT>').strip()    
                output=(curtime()+' '+ address+' '+ subric+' '+ message+'\n')
                # Doppelalarmierung check
                if address == poc_alt_address and message == poc_alt_message and utc_stamp < poc_alt_utc + 5:
                    print adress + " - POCSAG Doppenalarmierung - nichts unternommen"
                else:
                    print curtime(), address, subric, message                               
                    with open('POCSAG.txt','a') as f:
                        f.write(output)
                    #Datensatz einfuegen
                    cursor = connection.cursor()
                    cursor.execute("INSERT INTO "+str(TabellePOC)+" (time,ric,funktion,text,einsatz) VALUES (%s,%s,%s,%s,%s)",(curtime(),address,subric,message,'0',))
                    cursor.close()
                    connection.commit()
                poc_alt_address = address
                poc_alt_utc = utc_stamp
                poc_alt_message = message
            if not "Alpha:" in line:                                                    
                with open("POCSAG_KeinText.txt","a") as missed:
                    address = line[21:28].replace(" ", "").zfill(7)
                    subric = line[40:41].replace(" ", "").replace("3", "4").replace("2", "3").replace("1", "2").replace("0", "1")
                    print  curtime(), address, subric
                    missed.write(line)
                    #Datensatz einfuegen
                    cursor = connection.cursor()
                    cursor.execute("INSERT INTO "+str(TabellePOC)+" (time,ric,funktion,text,einsatz) VALUES (%s,%s,%s,%s,%s)",(curtime(),address,subric,'','0',))
                    cursor.close()
                    connection.commit()
                  
except KeyboardInterrupt:
    os.kill(multimon_ng.pid, 9)


# Datenbankdaten
dbserver = ""
dbuser = ""
dbpassword = ""
datenbank = ""
TabellePOC = "pocsag_history"
TabelleFMS = "fms_history"
TabelleZVEI = "zvei_history"

# Vor den Kanal ein O fÃ¼r Oberband - ein U fÃ¼r Unterband. 4m und 2m Band. Es werden nur die technischen KanÃ¤le 101-125 im 2m Band berÃ¼cksichtigt! 
kanal = ""

# Fehlerkorrektur ppm DVB-T Stick
ppmerror = "31"

# DVB-T Stick Device ID, Testen mit "rtl_test"
deviceid = "0"

# POCSAG512 - POCSAG1200 - POCSAG2400 - FMSFSK - ZVEI2
demod = "FMSFSK"

########################################
##### Userdaten ENDE               ##### 
########################################


frequenz = "0"
if kanal[0:2] == "U1":
   frequenz = ((int(kanal[1:4]) - 101) * 0.02) + 165.210
elif kanal[0:2] == "O1":
   frequenz = ((int(kanal[1:4]) - 101) * 0.02) + 169.810
elif kanal[0:1] == "O":
   frequenz = ((int(kanal[1:4]) - 347) * 0.02) + 84.015
elif kanal[0:1] == "U":
   frequenz = ((int(kanal[1:4]) - 347) * 0.02) + 74.215
print "eingestellter Kanal: " + kanal[1:4] + " " + kanal[0] + "B"
print "Kanalfrequenz: " + str(frequenz) + " MHz"
   
# ZVEI Filter Schleifen
zvei_filter = ['00000', '11111', '22222', '33333', '44444', '55555', '66666', '77777', '88888', '99999']
# MySQL Verbindung aufbauen
try:
    connection = mysql.connector.connect(host = str(dbserver), user = str(dbuser), passwd = str(dbpassword), db = str(datenbank))
except:
    print "Keine Verbindung zum Server"
    exit(0)

def curtime():
    return time.strftime("%Y-%m-%d %H:%M:%S")

with open('Fehler.txt','a') as file:
    file.write(('#' * 20) + '\n' + curtime() + '\n')

multimon_ng = subprocess.Popen("rtl_fm -d "+str(deviceid)+" -f "+str(frequenz)+"M -M fm -s 22050 -p "+str(ppmerror)+" -E DC -F 0 -g 100 | multimon-ng -a "+str(demod)+" -f alpha -t raw -",
                               #stdin=rtl_fm.stdout,
                               stdout=subprocess.PIPE,
                               stderr=open('error_marcel.txt','a'),
                               shell=True)

try:
    while True:
    
        
        line = multimon_ng.stdout.readline()
        multimon_ng.poll()
        with open('Line.txt','a') as a:
            a.write(line)
            
###### ZVEI - Abfrage ######
        if line.startswith('ZVEI2'):
         address = line[7:12].replace(" ", "")
         address = address.replace("\n","")
         address = address.replace("\r","")
         if len(address) == 5:
            
               ### Schleifen filtern 00000, 11111, ... ### 
               if address == any(zvei_filter) :
                print address + " - ZVEI ausgefiltert - nichts unternommen"
               ### Schleifen filtern /ENDE ###         
               else:
                utc_stamp = int(time.time())
                # Wiederholton 'F' auflÃ¶sen
                s1 = address[0]
                s2 = address[1]
                s3 = address[2]
                s4 = address[3]
                s5 = address[4]
                if s2 == "F":
                    s2 = s1    
                elif s3 == "F":
                    s3 = s2
                elif s4 == "F":
                    s4 = s3
                elif s5 == "F":
                    s5 = s4
                address2 = s1 + s2 + s3 + s4 + s5
                # Pruefen ob Schleife numerisch ist
               if address2.isdigit() is True:
                # Pruefen auf Doppelalarmierung
                  if address2 == alte_schleife and utc_stamp < alte_zeit + 3:
                     print address2 + " - ZVEI Doppelalarmierung - nichts unternommen"
                  else:
                     output=(curtime()+' '+ address2+'\n')
                     print curtime(), address2
                     with open('ZVEI.txt','a') as f:                                           
                       f.write(output)
                     cursor = connection.cursor()
                     cursor.execute("INSERT INTO "+str(TabelleZVEI)+" (time,schleife) VALUES (%s,%s)",(curtime(),address2,))
                     cursor.close()
                     connection.commit()
               else:
                   print address + " - ZVEI nicht numerisch - nichts unternommen"
               alte_zeit = utc_stamp
               alte_schleife = address2
         else:
               print address + " - ZVEI nicht vollstaendig - nichts unternommen"
               
###### FMS - Abfrage ######
        elif line.startswith('FMS'):
                    bos = line[19]
                    land = line[36]
                    kreis= line[65:67]
                    fhzg = line[72:76]
                    status = line[84]
                    richtung = line[101]
                    address = (bos+''+ land+''+ kreis+''+ fhzg)
                    output= (curtime()+' '+ bos+''+ land+''+ kreis+''+ fhzg+' '+status+' '+richtung+'\n')
                    print curtime(), address, status, richtung
                    with open('FMS.txt','a') as f:                                           
                        f.write(output)
                    cursor = connection.cursor()
                    cursor.execute("INSERT INTO "+str(TabelleFMS)+" (timestamp,kennung,status,richtung) VALUES (%s,%s,%s,%s)",(curtime(),address,status,richtung,))
                    cursor.close()
                    connection.commit()
                    
###### POCSAG - Abfrage ######
        elif line.__contains__("Alpha:"):                                                
                if line.startswith('POCSAG'):
                 address = line[21:28].replace(" ", "").zfill(7)                         
                 subric = line[40:41].replace(" ", "").replace("3", "4").replace("2", "3").replace("1", "2").replace("0", "1")
                 message = line.split('Alpha:   ')[1].strip().rstrip('<EOT>').strip()    
                 output=(curtime()+' '+ address+' '+ subric+' '+ message+'\n')           
                 print curtime(), address, subric, message                               
                 with open('POCSAG.txt','a') as f:
                     f.write(output)
                 #Datensatz einfÃ¼gen
                 cursor = connection.cursor()
                 cursor.execute("INSERT INTO "+str(TabellePOC)+" (time,ric,funktion,text) VALUES (%s,%s,%s,%s)",(curtime(),address,subric,message,))
                 cursor.close()
                 connection.commit()
                if not "Alpha:" in line:                                                    
                 with open("POCSAG_KeinText.txt","a") as missed:
                  address = line[21:28].replace(" ", "").zfill(7)
                  subric = line[40:41].replace(" ", "").replace("3", "4").replace("2", "3").replace("1", "2").replace("0", "1")
                  print  curtime(), address, subric
                  missed.write(line)
                  #Datensatz einfÃ¼gen
                  cursor = connection.cursor()
                  cursor.execute("INSERT INTO "+str(TabellePOC)+" (time,ric,funktion,text) VALUES (%s,%s,%s,%s)",(curtime(),address,subric,'',))
                  cursor.close()
                  connection.commit()
                  
except KeyboardInterrupt:
    os.kill(multimon_ng.pid, 9)
