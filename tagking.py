from __future__ import print_function
from dotenv import load_dotenv
from astrapy.db import AstraDB, AstraDBCollection
from astrapy.ops import AstraDBOps  



from github import Github

import os.path
import os
import json
import re

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

token = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
api_endpoint = os.getenv("ASTRA_DB_API_ENDPOINT")

astra_db = AstraDB(token=token, api_endpoint=api_endpoint)
tag_application_collection = AstraDBCollection(collection_name="tag_applications", astra_db=astra_db)
collection = AstraDBCollection(
    collection_name="tag_applications", token=token, api_endpoint=api_endpoint
)

# using an access token
f = open("github.token", "r")
line = f.readlines()[0].replace("\n", "")
g = Github(line)

p = re.compile('[a-zA-Z]+')

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = '1vJSKJAa7EJ0s1Ksn_L_lgQGJI6-UMDqNngrQO4U4cEY'
SAMPLE_RANGE_NAME = 'SampleApplicationMain'


def main():
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    print("Starting")
    entries = []
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing creds")
            try:
                creds.refresh(Request())
            except:
                print("ERROR")
        else:
            print("Using creds")
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    print("Building service")
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    print("Getting sample application links")
    # Call the Sheets API for SampleApplication links
    result = service.spreadsheets().get(spreadsheetId=SAMPLE_SPREADSHEET_ID, ranges=SAMPLE_RANGE_NAME,
                                        fields="sheets/data/rowData/values/hyperlink,sheets/data/rowData/values/textFormatRuns/format/link/uri").execute()
    values = result.get('sheets', [])

    sampleApplicationLinks = values[0]["data"][0]["rowData"]
    print("Got sample application links")

    print("Getting sample application items")
    # Call the Sheets API for SampleApplication items
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=SAMPLE_RANGE_NAME).execute()
    sampleApplicationItems = result.get('values', [])
    print("Got sample application items")
    # Workshop sheet for links
    WORKSHOP_SAMPLE_RANGE_NAME = 'WorkshopCatalog'

    print("Getting workshop links")
    # Call the Sheets API for Workshop Links
    result = service.spreadsheets().get(spreadsheetId=SAMPLE_SPREADSHEET_ID, ranges=WORKSHOP_SAMPLE_RANGE_NAME,
                                        fields="sheets/data/rowData/values/hyperlink,sheets/data/rowData/values/textFormatRuns/format/link/uri").execute()
    values = result.get('sheets', [])
    workshopLinks = values[0]["data"][0]["rowData"]

    print("Got workshop links")
    print("Getting workshop items")
    # Get the items for Workshops
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=WORKSHOP_SAMPLE_RANGE_NAME).execute()
    workshopItems = result.get('values', [])
    print("Got workshop items")
    counter = 0
    github = {}
    for entry in sampleApplicationItems:
        urls = {"heroimage":"https://yt3.googleusercontent.com/ytc/AMLnZu99z7O76h-EBAOloogUjeaXsi0HN-2YaiixWxAjyw=s176-c-k-c0x00ffffff-no-rj-mo"}
        if counter == 0:
            counter += 1
            continue

        counter += 1
        summary = ""
        if '\n' in entry[0]:
            (name, summary) = entry[0].split('\n')
        else:
            if entry[0] == "":
                continue
            name = entry[0]

        links = sampleApplicationLinks
        if (len(links) > counter-1 and "values" in links[counter-1]):
            urlcheck = links[counter-1]["values"]
            getLinks(urlcheck, urls)

        tags = []
        language = []
       # Language
        if (entry[2] != [""]):
            language = entry[2].split(",")
            for item in language:
                tags.append(item.lower())

        # Stack should be an array
        if (entry[3] != [""]):
            stack = entry[3].split(",")
            for item in stack:
                tags.append(item.lower())

        # APIs
        entrynumber = 6
        apiarray = []
        for api in ["DATA", "DOC", "GQL", "CQL", "GRPC", "DB", "IAM", "STRM"]:
            if entry[entrynumber] == 'TRUE':
                apiarray.append(api)
            entrynumber += 1

        newtags = cleanTags(tags)

        new_item = {
            "name": name,
            "summary": summary,
            "urls": urls,
            "language": language,
            "stack": stack,
            "usecases": entry[4],
            "owner": entry[5],
            "apis": apiarray,
            "tags": newtags
        }

        entries.append(new_item)

    counter = 0

    for entry in workshopItems:
        urls = {}
        tags = []
        if counter <= 1:
            counter += 1
            continue

        if (len(entry) == 0):
            continue
        counter += 1
        summary = ""

        if '\n' in entry[0]:
            (name, summary) = entry[0].split('\n')
            code = ""
        else:
            code = entry[0]

        links = workshopLinks

        if (len(links) > counter-1 and "values" in links[counter-1]):
            urlcheck = links[counter-1]["values"]
            addurl = ""
            getLinks(urlcheck, urls)

        if (len(entry) >= 8):
            taglist = entry[7].replace(',', "\n").split('\n')
            for tag in taglist:
                tags.append(tag.lower())

        tags.append("workshop")
        newtags = cleanTags(tags)

        new_item = {
            "code": code,
            "name": entry[2].replace("\n", ""),
            "tags": newtags,
            "urls": urls
        }

        entries.append(new_item)

    githublinks = []
    for index in range(len(entries)):
        readme = ""
        keys = {}
        entry = entries[index]
        if ("github" in entry["urls"]):
            for url in entry["urls"]["github"]:
                if "github" not in url:
                    continue
                githublinks.append(url)
                owner = url.split('/')[3]
                reponame = url.split('/')[4]
                repo = g.get_repo(owner + "/" + reponame)
                # Get the README

    # Just for fun, get all the repos for Datastax-Examples
    organization = g.get_organization('Datastax-Examples')
    for repo in organization.get_repos():
        url = repo.raw_data["html_url"]
        if url not in githublinks:
            entries.append( {"urls":{"github":url}})

    uniquelinks = []
    for index in range(len(entries)):
        astrajson = ""
        keys = {}
        entry = entries[index]
        if ("github" in entry["urls"]):
            for url in entry["urls"]["github"]:
                if "github" not in url:
                    continue
                if url in uniquelinks:
                    del entries[index]
                    continue
                owner = url.split('/')[3]
                reponame = url.split('/')[4]
                repo = g.get_repo(owner + "/" + reponame)
                try:
                    astrajson = repo.get_contents("astra.json")
                except:
                    continue
                settings = json.loads(astrajson.decoded_content.decode())
                keys = settings.keys()
                for key in keys:
                    lowerkey = key.lower()
                    if (key.upper() == "GITHUBURL"):
                        continue
                    elif (key.upper() == "GITPODURL"):
                        entries[index]["urls"]["gitpod"] = [settings[key]]
                    elif (key.upper() == "NETLIFYURL"):
                        entries[index]["urls"]["netlify"] = [settings[key]]
                    elif (key.upper() == "DEMOURL"):
                        entries[index]["urls"]["demo"] = [settings[key]]
                    elif (key.upper() == "VERCELURL"):
                        entries[index]["urls"]["vercel"] = [settings[key]]
                    elif (key.upper() == "TAGS"):
                        for tag in settings["tags"]:
                            if ("name" in tag):
                                entries[index]["tags"].append(
                                    tag["name"].lower())
                            else:
                                entries[index]["tags"].append(tag.lower())
                    elif (key.upper() == "STACK"):
                        for stack in settings["stack"]:
                            if ("tags" not in entries[index]):
                                entries[index]["tags"] = []
                            entries[index]["tags"].append(stack.lower())
                    elif (key.upper() == "CATEGORY"):
                        entries[index]["tags"].append(settings[key])
                    elif (key.upper() == "HEROIMAGE"):
                        entries[index]["urls"]["heroimage"] = settings[key]
                    else:
                        entries[index][lowerkey] = settings[key]
                if "tags" in entries[index]:
                    entries[index]["tags"] = cleanTags(entries[index]["tags"])

    tagdict = {}
    tagdict["all"] = {}
    tagdict["all"]["apps"] = []

    for entry in entries:
        if "name" not in entry:
            entries.remove(entry)
        if "tags" in entry:
            for tag in entry["tags"]:
                if tag.lower() not in tagdict.keys():
                    tagdict[tag.lower()] = {
                        "name": tag.lower(), "apps": [entry]}
                else:
                    tagdict[tag.lower()]["apps"].append(entry)

    names = []

    # Remove dupes in all
    for tag in tagdict.keys():
        for app in tagdict[tag]["apps"]:
            if app["name"] not in names:
                tagdict["all"]["apps"].append(app)
                names.append(app["name"])
                print ("Setting up to skip " + app["name"])
            else:
                print("Skipping " + app["name"])

    for tag in tagdict.keys():
        count = len(tagdict[tag]["apps"])
        tagdict[tag]["count"] = count

        try:
            res = tag_collection.create(
                document={"name": tag, "count": count, tag: tagdict[tag]}, path=tag)
            print(res)
        except:
            print("ERROR")
            print(res)


def cleanTags(tags):
    newtags = []
    for tag in tags:
        if not (p.match(tag)):
            continue
        if tag in ("doc api", "documentapi", "docapi", "document api"):
            tag = "doc api"
        if tag in ("gql api", "graphql"):
            tag = "graphql api"
        if tag in ("java", "java driver"):
            tag = "java"
        if tag in ("spring-boot", "spring-data", "spring", "spring-webflux"):
            tag = "spring"
        if tag not in newtags:
            newtags.append(tag)
    return newtags


def addURL(urlitem, index, urls):
    if index == 1:
        if "badge" not in urls:
            urls["badge"] = []
        urls["badge"].append(urlitem)
        urls["heroimage"] = urlitem
    if index == 3:
        if "slides" not in urls:
            urls["slides"] = []
        urls["slides"].append(urlitem)
    if index == 4:
        if "github" not in urls:
            urls["github"] = []
        urls["github"].append(urlitem)
    if index == 5:
        if "menti" not in urls:
            urls["menti"] = []
        urls["menti"].append(urlitem)
    if index == 6:
        if "abstract" not in urls:
            urls["abstract"] = []
        urls["abstract"].append(urlitem)
    if index == 9:
        if "youtube" not in urls:
            urls["youtube"] = []
        urls["youtube"].append(urlitem)


def getLinks(urlcheck, urls):
    for index in range(len(urlcheck)):
        if "textFormatRuns" in urlcheck[index]:
            for textFormatRuns in range(len(urlcheck[index]["textFormatRuns"])):
                if "link" in urlcheck[index]["textFormatRuns"][textFormatRuns]["format"]:
                    urlitem = urlcheck[index]["textFormatRuns"][textFormatRuns]["format"]["link"]["uri"]
                    if ("github" in urlitem):
                        addURL(urlitem, 4, urls)
                    else:
                        addURL(urlitem, index, urls)
        if "hyperlink" in urlcheck[index]:
            urlitem = urlcheck[index]["hyperlink"]
            addURL(urlitem, index, urls)


if __name__ == '__main__':
    main()
