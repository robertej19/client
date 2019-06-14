#!/usr/bin/env python
#****************************************************************
"""
# This is the submission script for use on the client side. Takes in an scard.txt file.
# Default file name is "scard.txt" which must be located in running directory, or can be specified
# directly by executing "python SubMit.py /path/to/scard/scard_name.txt. This will query the computer
# for username and domainname information, add to the databse, then reads the scard, downloads any
# gcards or other files from online repositories, and inserts the inforamtion into the database.
# Please note the database must exist for this to work properly. If the database does not exist
# (while we are using SQLite): go to the server side code and generate the database. Consult the
# most recent README for specific directions on accomplishing this.
"""
#****************************************************************

from __future__ import print_function
import argparse, os, sqlite3, subprocess, sys, time
from subprocess import PIPE, Popen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))+'/../../')
#Could also do the following, but then python has to search the
#sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import file_struct, gcard_helper, scard_helper, user_validation, utils

def Batch_Entry(args):
    timestamp = utils.gettime() # Can modify this if need 10ths of seconds or more resolution
    strn = """INSERT INTO Batches(timestamp) VALUES ("{0}");""".format(timestamp)
    BatchID = utils.sql3_exec(strn)
    scard_file = args.scard

    #Write the text contained in scard.txt to a field in the Batches table
    with open(scard_file, 'r') as file: scard = file.read()
    strn = """UPDATE Batches SET {0} = '{1}' WHERE BatchID = "{2}";""".format('scard',scard,BatchID)
    utils.sql3_exec(strn)
    utils.printer("Batch specifications written to database with BatchID {0}".format(BatchID))

    #See if user exists already in database; if not, add them
    with open(scard_file, 'r') as file: scard_text = file.read()
    scard_fields = scard_helper.scard_class(scard_text)
    username = user_validation.user_validation()

    #Write scard into scard table fields (This will not be needed in the future)
    print("\nReading in information from {0}".format(scard_file))
    utils.printer("Writing SCard to Database")
    scard_fields.data['group_name'] = scard_fields.data.pop('group') #'group' is a protected word in SQL so we can't use the field title "group"
    # For more information on protected words in SQL, see https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=RSQL_reservedwords

    if 'https://' in scard_fields.data.get('generator'):
      print("Online repository for generator files specified; will download on server")
      scard_fields.data['genExecutable'] = "Null"
      scard_fields.data['genOutput']     = "Null"
      scard_fields.data['genOptions']    = "Null"
      scard_fields.data['nevents']       = "User Lund File Driven"
      scard_fields.data['jobs']          = "One per User Lund File"
    else:
      scard_fields.data['genExecutable'] = file_struct.genExecutable.get(scard_fields.data.get('generator'))
      scard_fields.data['genOutput']     = file_struct.genOutput.get(scard_fields.data.get('generator'))

    scard_helper.SCard_Entry(BatchID,timestamp,scard_fields.data)
    print('\t Your scard has been read into the database with BatchID = {0} at {1} \n'.format(BatchID,timestamp))


    strn = "SELECT UserID FROM Users WHERE User = '{}';".format(username)
    userid = utils.sql3_grab(strn)[0][0]
    #Write gcards into gcards table
    utils.printer("Writing GCards to Database")
    gcard_helper.GCard_Entry(BatchID,timestamp,scard_fields.data['gcards'])
    print("Successfully added gcards to database")
    strn = "UPDATE Batches SET {0} = '{1}' WHERE BatchID = {2};".format('UserID',userid,BatchID)
    utils.sql3_exec(strn)

    strn = "UPDATE Batches SET {0} = '{1}' WHERE BatchID = {2};".format('User',username,BatchID)
    utils.sql3_exec(strn)


    strn = "SELECT GcardID, gcard_text FROM Gcards WHERE BatchID = {0};".format(BatchID)
    gcards = utils.sql3_grab(strn)
    for gcard in gcards:
      GcardID = gcard[0]
      strn = "INSERT INTO Submissions(BatchID,GcardID) VALUES ({0},{1});".format(BatchID,GcardID)
      utils.sql3_exec(strn)
      strn = "UPDATE Submissions SET submission_pool = '{0}' WHERE GcardID = '{1}';".format(scard_fields.data['farm_name'],GcardID)
      utils.sql3_exec(strn)
      strn = "UPDATE Submissions SET run_status = 'Not Submitted' WHERE GcardID = '{0}';".format(GcardID)
      utils.sql3_exec(strn)

    return 0

if __name__ == "__main__":
  argparser = argparse.ArgumentParser()
  argparser.add_argument('scard',help = 'relative path and name scard you want to submit, e.g. ../scard.txt')
  argparser.add_argument(file_struct.debug_short,file_struct.debug_longdash, default = file_struct.debug_default,help = file_struct.debug_help)
  argparser.add_argument('-l','--lite',help = "use -l or --lite to connect to sqlite DB, otherwise use MySQL DB", action = 'store_false')
  args = argparser.parse_args()

  file_struct.DEBUG = getattr(args,file_struct.debug_long)
  file_struct.use_mysql = args.lite

  if args.lite:
    exists = """insert some connection to mysql db test"""
  else:
    exists = os.path.isfile(file_struct.SQLite_DB_path+file_struct.DB_name)

  if args.scard:
    if exists:
        Batch_Entry(args)
    else:
        print('Could not find SQLite Database File. Are you sure it exists and lives in the proper location? Consult README for help')
        exit()
  else:
    print('SubMit.py requires an scard.txt file to submit a job. You can find an example listed in the documentation \n')
    print('Proper usage is `SubMit.py <name of scard file>` e.g. `SubMit.py scard.txt`')
    exit()
