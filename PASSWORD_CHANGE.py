import os
import re
import sys
import time
import yaml
import shutil
import jinja2
import socket
import random
import logging
import netmiko
from threading import Thread
import queue as queue
from ISEFunctions import *
from EmailModule import emailHTMLWithRenamedAttachment

def COMMANDS( login_username,login_password,username,new_password,counter,device_type,devices,deviceList,outputList,CIMC):
    while not deviceList.empty():
        device = deviceList.get_nowait()
        if not CIMC:
            try:

                # Connection Break
                counter = len(devices)-deviceList.qsize()
                print('\n['+str(counter)+'] Connecting to: '+device+'\n')
                outputList.put('\n['+str(counter)+'] Connecting to: '+device+'\n')
                # Connection Handler
                connection = netmiko.ConnectHandler(ip=device, device_type=device_type, username=login_username, password=login_password, global_delay_factor=9)

                # Change WebGui Password
                output = connection.send_command_timing('application reset-passwd ise '+username)
                if 'Password reset is only possible' in  output:
                    print('Error')
                else:
                    connection.send_command_timing(new_password)
                    connection.send_command_timing(new_password)
                # Change CLI Password
                connection.send_command_timing('conf t')
                connection.send_command_timing('username '+username+' password plain '+new_password+' role admin')
                connection.send_command_timing('end')
                connection.send_command_timing('wr mem')
                connection.send_command_timing('\n\n\n\n')

                outputList.put(('!\n['+str(counter)+'] PASSWORD CHANGE: PASSWORD CHANGE COMPLETED - '+device+'\n!'))
                try:
                    connection.disconnect()
                except OSError:
                    pass
                except:
                    outputList.put(('\n!'+'\n!'+'\n['+str(counter)+'] PASSWORD CHANGE: DISCONNECT ERROR - '+device+'\n!'+'\n!'))



            except:    # exceptions as exceptionOccured:
                outputList.put(('\n!'+'\n!'+'\n['+str(counter)+'] PASSWORD CHANGE: CONNECTION ERROR - '+device+'\n!'+'\n!'))
        else:
            try:

                # Connection Break
                counter = len(devices)-deviceList.qsize()
                print('\n['+str(counter)+'] Connecting to: '+device+'\n')
                outputList.put('\n['+str(counter)+'] Connecting to: '+device+'\n')
                # Connection Handler
                connection = netmiko.ConnectHandler(ip=device, device_type=device_type, username=login_username, password=login_password, global_delay_factor=9)
                # Find Local user index
                output = connection.send_command_timing('show user')
                for line in output.strip().splitlines():
                    line = line.split()
                    if username == line[1]:
                        user_index = line[0]
                if not user_index:
                    outputList.put(('\n['+str(counter)+'] PASSWORD CHANGE: USER ('+username+') NOT FOUND - '+device+'\n!'))
                    raise Exception
                # Change  Password
                connection.send_command_timing('scope user '+user_index)
                output = connection.send_command_timing('set password')
                if 'Please enter password' not in  output:
                    outputList.put(('\n['+str(counter)+'] PASSWORD CHANGE: ERROR CHANGING PASSWORD - '+device+'\n!'))
                    raise Exception
                else:
                    connection.send_command_timing(new_password)
                    connection.send_command_timing(new_password)
                # Change CLI Password
                connection.send_command_timing('commit')
                connection.send_command_timing('exit')
                connection.send_command_timing('exit')

                outputList.put(('!\n['+str(counter)+'] PASSWORD CHANGE: PASSWORD CHANGE COMPLETED - '+device+'\n!'))
                try:
                    connection.disconnect()
                except OSError:
                    pass
                except:
                    outputList.put(('\n!'+'\n!'+'\n['+str(counter)+'] PASSWORD CHANGE: DISCONNECT ERROR - '+device+'\n!'+'\n!'))



            except:    # exceptions as exceptionOccured:
                outputList.put(('\n!'+'\n!'+'\n['+str(counter)+'] PASSWORD CHANGE: CONNECTION ERROR - '+device+'\n!'+'\n!'))
    outputList.put(None)
    return

def script(form,configSettings):

    # Pull variables from web form
    deployment = form['deployment']
    login_username = form['login_username']
    login_password = form['login_password']
    username = form['username']
    new_password = form['new_password']
    email = form['email']

    # Netmiko Device Type
    device_type = 'linux'


    NAC_NA = [
        'USNAC1.domain.com',
        'USNAC2.domain.com',
    ]
    NAC_EU = [
        'EUNAC1.domain.com',
        'EUNAC2.domain.com',
    ]
    NAC_AP = [
        'APNAC1.domain.com',
        'APNAC2.domain.com',
    ]
    NDA = [
        'USNAC3.domain.com',
        'USNAC4.domain.com',
    ]
    NAC_NA_CIMC = [
        'USNAM1.domain.com',
        'USNAM2.domain.com',
    ]
    NAC_EU_CIMC = [
        'EUCIMC1.domain.com',
        'EUCIMC1.domain.com',
    ]
    NAC_AP_CIMC = [
        'APCIMC1.domain.com',
        'APCIMC2.domain.com',
    ]
    NDA_CIMC = [
        'USCIMC3.domain.com',
        'USCIMC4.domain.com',
    ]


    CIMC = False
    if deployment == 'NAC_NA':
        devices = NAC_NA
    elif deployment == 'NAC_EU':
        devices = NAC_EU
    elif deployment == 'NAC_AP':
        devices = NAC_AP
    elif deployment == 'NDA':
        devices = NDA
    elif deployment == 'NAC_NA_CIMC':
        devices = NAC_NA_CIMC
        CIMC = True
    elif deployment == 'NAC_EU_CIMC':
        devices = NAC_EU_CIMC
        CIMC = True
    elif deployment == 'NAC_AP_CIMC':
        devices = NAC_AP_CIMC
        CIMC = True
    elif deployment == 'NDA_CIMC':
        devices = NDA_CIMC
        CIMC = True

    # Define Threading Queues
    NUM_THREADS = 20
    deviceList = queue.Queue()
    outputList = queue.Queue()

    if len(devices) < NUM_THREADS:
        NUM_THREADS = len(devices)
    for line in devices:
        deviceList.put(line.strip())


    # Random Generated Output File
    outputDirectory = ''
    outputFileName = ''
    for i in range(6):
        outputDirectory += chr(random.randint(97,122))
    outputDirectory += '/'
    if not os.path.exists(outputDirectory):
        os.makedirs(outputDirectory)
    for i in range(6):
        outputFileName += chr(random.randint(97,122))
    outputFileName += '.txt'

    counter = 0

    # loop for devices
    for i in range(NUM_THREADS):
        Thread(target=COMMANDS, args=(login_username,login_password,username,new_password,counter,device_type,devices,deviceList,outputList,CIMC)).start()
        time.sleep(1)

    with open(outputFileName,'w') as outputFile:
        numDone = 0
        while numDone < NUM_THREADS:
            result = outputList.get()
            if result is None:
                numDone += 1
            else:
                outputFile.write(result)

    ##############################
    # Email Out Result
    #
    subject = 'Results for ISE Password Change'
    html = """
    <html>
    <body>
    <h1>Output from ISE Password Change Script</h1>
    </body>
    </html>
    """
    attachmentfile = outputFileName
    attachmentname = 'results.csv'
    #
    From = 'NAC Migration <NAC_Migration@domain.com>'
    #
    emailHTMLWithRenamedAttachment(email,subject,html,attachmentfile,attachmentname,From)
	
    # Delete Directory and Output File
    if os.path.exists(outputDirectory):
        shutil.rmtree(outputDirectory,ignore_errors=True)
    os.remove(outputFileName)

    return
