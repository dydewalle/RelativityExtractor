#Checks if all external dependencies are installed and installs them if not
#import setup
#setup.Main()

#Packages
import requests
import base64
import os
import json
import csv
import sys
import pandas as pd
from datetime import datetime

def getLogin():
    answered = False
    result = ""

    while answered == False:
        clientID = input("Please enter your Relativity Client ID: ")
        clientSecret = input("Please enter your Relativity Client Secret: ")

        if clientID == "" or clientSecret == "":
            answered = False
            print("\nYou didn't enter all required fields.\n")
        else:
            userpass = f"client_id={clientID}&client_secret={clientSecret}&scope=SystemUserInfo&grant_type=client_credentials"
            answered = True

            apiurl = f'https://forcyd.relativity.one/Relativity/Identity/connect/token'
            response = requests.post(apiurl, headers={'X-CSRF-Header': '-', 'Content-Type': 'application/x-www-form-urlencoded'},data=userpass)
            response_json = json.loads(response.text)
            result = response_json["access_token"]
            
    return result

def getWorkspaceSelection():
    answered = False

    while answered == False:
        workspaceID = input("Please provide workspace ID: ")


        if workspaceID == "":
            answered = False
            print("\nYou didn't enter all required fields.\n")
        else:
            answered = True

    print("")
    
    return workspaceID

def getMonth():
    answered = False

    while answered == False:
        period = input("Please provide year and month (format: YYYYMM): ")


        if period == "":
            answered = False
            print("\nYou didn't enter all required fields.\n")
        else:
            answered = True

    print("")
    
    return period

def getAuditActionFieldID(credentials, workspaceID):
    artifactID = 0
    
    #API call to obtain all the parent choices of the Action Data Grid Audit field.
    apiurl = f'https://forcyd.relativity.one/Relativity.REST/API/Relativity.ObjectManager/v1/workspace/{workspaceID}/object/queryslim'
    print(apiurl)
    response = requests.post(apiurl, headers={'Authorization': credentials, 'X-CSRF-Header': '-', 'Content-Type': 'application/json'},json={
        "Request": {
            "ObjectType" : {
                    "Name": "Field"
             }
            ,"fields": [
                {
                    "Name": "Artifact ID"
                }
            ],
            "condition": "(('Name' == 'Action') AND ('Object Type' == 'Data Grid Audit'))"
        },
        "start": 1,
        "length": 1
    })

    # Convert JSON into array with named index
    data = json.loads(response.text)
    artifactID = data["Objects"][0]["Values"][0]
    
    return artifactID

def getAuditActionList(credentials, workspaceID):
    actionList = []
    
    #API call to obtain all the choices of the Action Data Grid Audit field.
    apiurl = f'https://forcyd.relativity.one/Relativity.REST/API/Relativity.ObjectManager/v1/workspace/{workspaceID}/object/queryslim'
    print(apiurl)
    response = requests.post(apiurl, headers={'Authorization': credentials, 'X-CSRF-Header': '-', 'Content-Type': 'application/json'},json={
        "Request": {
            "ObjectType" : {
                    "Name": "Code"
             }
            ,"fields": [
                {
                    "Name": "Artifact ID"
                },
                {
                    "Name": "Name"
                }
            ],
            "condition": f"(('Field' == 'Action') AND ('Object Type' == 'Data Grid Audit'))"
        },
        "start": 1,
        "length": 100
    })

    # Convert JSON into array with named index
    data = json.loads(response.text)
    for value in data["Objects"]:
        actionList.append([value["Values"][1],value["ArtifactID"]])
    
    return actionList

def getValueList(listItems, requestedIndex):
    data = ""

    for value in listItems:
        if value[0] == requestedIndex:
            return str(value[1])

    return ""


def getApiLog(credentials, workspaceID, listActions, period):
    result = ""

    periodYear_start = period[:4]
    periodMonth_start = period[-2:]
    if periodMonth_start == "12":
        periodYear_end = str(int(periodYear_start) + 1)
        periodMonth_end = "01"
    else:
        periodYear_end = periodYear_start
        periodMonth_end = str(int(periodMonth_start) + 1)

    if len(periodMonth_end) == 1:
        periodMonth_end = "0" + periodMonth_end


    
    #API call for the regular keyword search (not including index searches).
    apiurl = f'https://forcyd.relativity.one/Relativity.REST/API/relativity-audit/v1/workspaces/{workspaceID}/audits/UI/query/'
    response = requests.post(apiurl, headers={'Authorization': credentials, 'X-CSRF-Header': '-', 'Content-Type': 'application/json'},json={
        "request": {
            "fields": [
                {
                    "Name": "Audit ID"
                },
                {
                    "Name": "User Name"
                },
                {
                    "Name": "Timestamp"
                },
                {
                    "Name": "Object Name"
                },
                {
                    "Name": "Action"
                }
            ],
            "condition": f"(('Action' IN CHOICE [{listActions}])) AND (('Timestamp' >= {periodYear_start}-{periodMonth_start}-01T00:00:00.00Z AND 'Timestamp' <= {periodYear_end}-{periodMonth_end}-01T00:00:00.00Z))",
            "rowCondition": "",
            "executingViewId": 1038474
        },
        "start": 1,
        "length": 10000
    })

    #print(response)
    data = json.loads(response.text)
    
    return data


def Main():
    #######################
    ##### GENERAL #########
    #######################
    
    #Prompts the user to fill in their Relativity Client ID and Secret
    token = getLogin()
    credentials = f"Bearer {token}"

    #Prompts the user to fill in the Workspace ID
    workspaceID = getWorkspaceSelection()

    #actionFieldID = getAuditActionFieldID(credentials, workspaceID)
    #print(str(actionFieldID))

    #Get a list of all the possible actions for Audit
    actionList = getAuditActionList(credentials, workspaceID)
    
    #currently interested in following actions: Query, Run, View, Update, Update - Mass Edit, Export
    strActions = getValueList(actionList, "Query") + ", " + getValueList(actionList, "Run") + ", " + getValueList(actionList, "View") + ", " + getValueList(actionList, "Update") + ", " + getValueList(actionList, "Update - Mass Edit") + ", " + getValueList(actionList, "Export")

    loopAudit = True
    while loopAudit:
        #Prompt user to get the period of interest
        period = getMonth()

        #request audit history
        auditLog = getApiLog(credentials, workspaceID, strActions, period)

        fileNamePrefix = str(workspaceID) + "-" + str(period) + "-"
        fileNameEndfix = "-" + str(datetime.now().strftime('%Y%m%d_%H%M%S')) + ".csv"

        #Convert results to array
        listAudit = []
        for record in auditLog["Objects"]:
            data = {
                    "AuditID": record["Name"],
                    "Timestamp": record["FieldValues"][2]["Value"],
                    "User": record["FieldValues"][1]["Value"]["Name"],
                    "Action": record["FieldValues"][4]["Value"]["Name"]}
        
            listAudit.append(data)
        
        #df = pd.json_normalize(auditLog["Objects"])
        df = pd.DataFrame(listAudit)

        
        pivot = pd.pivot_table(df, 
                               index='User', 
                               columns='Action', 
                               values='AuditID', 
                               aggfunc='count', 
                               fill_value=0)

        #Print pivot
        print(pivot)

        loopIndicator = input("Do you want to proceed with another period (y/n): ")
        if loopIndicator == "y":
            loopAudit = True
        else:
            loopAudit = False

    print("Done!!!!")


Main()
