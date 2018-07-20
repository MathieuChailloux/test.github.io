# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Utils
                                 A QGIS plugin
 Computes ecological continuities based on environments permeability
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2018-04-12
        git sha              : $Format:%H$
        copyright            : (C) 2018 by IRSTEA
        email                : mathieu.chailloux@irstea.fr
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import datetime
import os.path
import pathlib
import sys
import subprocess

file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)

# Log utilities

debug_flag=True

def printDate(msg):
    print ("[" + str(datetime.datetime.now()) + "] " + msg)
    
def debug(msg):
    if debug_flag:
        printDate("[debug] " + msg)
    
def info(msg):
    printDate("[info] " + msg)
    
def warn(msg):
    printDate("[warn] " + msg)
    
def user_error(msg):
    printDate("[user error] " + msg)
    raise Exception(msg)
    
def internal_error(msg):
    printDate("[internal error] " + msg)
    raise Exception(msg)
    
def todo_error(msg):
    printDate("[Feature not yet implemented] " + msg)
    raise Exception(msg)

    
# File utils
    
def normPath(fname):
    return fname.replace('\\','/')
    
def checkFileExists(fname,prefix=""):
    if not (os.path.isfile(fname)):
        user_error(prefix + "File '" + fname + "' does not exist")
        
def removeFile(path):
    info("Deleting existing file '" + path + "'")
    os.remove(path)
    
        
def writeFile(fname,str):
    with open(fname,"w",encoding="utf-8") as f:
        f.write(str)
    

# Type utils
    
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
    
def is_integer(s):
    try:
        int(s)
        return True
    except ValueError:
        return False
        
        
# Validity checkers
        
def checkFields(ref_fields,fields):
    if ref_fields != fields:
        for rf in ref_fields:
            if rf not in fields:
                user_error("Missing field '" + rf + "'")
             
def checkDictField(item,fieldname,prefix=None):
    if prefix == None:
        prefix = item.__class__.name
    if not item.dict[fieldname]:
        user_error(prefix + " with empty name '" + str(item.dict[fieldname]) + "'")
        
def checkName(item,prefix=None):
    checkDictField(item,"name",prefix)
    
def checkDescr(item,prefix=None):
    if prefix == None:
        prefix = item.__class__.name
    if not item.dict["descr"]:
        warn(prefix + " with empty name '" + str(item.dict["descr"]) + "'")
        

# Subprocess utils
        
def executeCmd(cmd_args):
    p = subprocess.Popen(cmd_args,
                         stderr=subprocess.PIPE,
                         stdout=subprocess.PIPE)
    out,err = p.communicate()
    debug(str(p.args))
    info(str(out))
    if err:
        if "invalid value encountered in less" in str(err):
            warn(str(err))
        else:
            user_error(str(err))
        
def executeCmdAsScript(cmd_args):
    debug("executeCmdAsScript")
    new_args = [sys.executable] + cmd_args
    debug(str(new_args))
    ret = subprocess.call(new_args)
    debug("return code = " + str(ret))
    
        