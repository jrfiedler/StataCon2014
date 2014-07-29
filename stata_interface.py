from IPython.core.magic import (Magics, magics_class, line_cell_magic)
from IPython.display import Image, IFrame
from ctypes import cdll
import win32com.client
import time
import os
import re



#-------------------------------------------------------------------------
# customization
#-------------------------------------------------------------------------

# The log file will be saved here.
# Create this directory if it doesn't already exist.
LOG_LOCATION = "C:/Users/jf/Documents/StataNotebooks/"

# Image files of plots will be saved here.
# Create this directory if it doesn't already exist.
GRAPH_LOCATION = "C:/Users/jf/Documents/StataNotebooks/"

# Help files converted to html will be saved here.
# Create this directory if it doesn't already exist.
HELP_HTML_LOCATION = "C:/Users/jf/Documents/StataNotebooks/help_files"  

# Hlp files will be searched for along the adopath.
# Change this if your adopath differs.
ADOPATH = [
    'C:/Program Files (x86)/Stata13/ado/base/',
    'C:/Program Files (x86)/Stata13/ado/site/',
    '.',
    'C:/ado/personal/',
    'C:/ado/plus/',
    'C:/ado/'
]

#-------------------------------------------------------------------------



pyre = re.compile(r'^\s*((%){0,2}py(thon)?\s)')


_sopen = cdll.msvcrt._sopen
_close = cdll.msvcrt._close
_SH_DENYRW = 0x10

def is_open(filename):
    if not os.access(filename, os.F_OK):
        return False # file doesn't exist
    h = _sopen(filename, 0, _SH_DENYRW, 0)
    if h == 3:
        _close(h)
        return False # file is not opened by anyone else
    return True # file is already open

    

i = 0
log_address = os.path.join(LOG_LOCATION , "log{}.txt".format(i))
while is_open(log_address) and i < 50:
    i += 1
    log_address = os.path.join(LOG_LOCATION , "log{}.txt".format(i))
    
    
ip = get_ipython()


CURRENT_CMD = ""
CMD_TIME = time.time()

class StataEvents:
    def OnFinish(self, *args):
        global CURRENT_CMD
        print("")


stataProg = win32com.client.Dispatch("stata.StataOLEApp")
st_do = stataProg.DoCommandAsync
st_do("log using {} , text replace".format(log_address))
st_do("set more off")

time.sleep(0.5)
log_file = open(log_address)

image_cmds = ("twoway", "scatter", "line", "hist", "histogram")

def print_output():
    time.sleep(1)
    line_count = 0
    log_line = log_file.readline()
    while log_line:
        print(log_line[:-1])
        log_line = log_file.readline()
        
def suppress_output():
    """displays output only if there was an error"""
    time.sleep(0.5)
    error = False
    output = ""
    line_count = 0
    log_line = log_file.readline()
    while log_line:
        output += log_line
        if log_line[:2] == "r(": error = True
        log_line = log_file.readline()
    if error:
        return output
    return None

def get_graph():
    global GRAPH_LOCATION

    pre = time.time()
    filename = os.path.join(GRAPH_LOCATION, "graph.png")
    st_do("    graph export \"{}\" , as(png) replace".format(filename))
        
    output = suppress_output()
    if output is not None:  # error occurred
        print(output)
        return
        
    file_time = pre - 1
    while file_time <= pre and (time.time() - pre) < 8:
        time.sleep(0.125)
        try:
            file_time = os.path.getmtime(filename)
        except WindowsError:
            continue
    try:
        return Image(filename=filename)
    except IOError:
        print("[could not find image file]")
    
def make_help(path, sthlp_name):
    sthlp_path = os.path.join(path, sthlp_name)
    html_name = sthlp_name.replace(".sthlp", ".html").replace(".hlp", ".html")
    saveas_path = os.path.join(HELP_HTML_LOCATION, html_name)
    st_do("qui sthlp2html \"" + sthlp_path + "\" , scheme(black) saveas(" + saveas_path + ")")
    
def display_help(filename):
    pre = time.time()
    full_path = os.path.join(HELP_HTML_LOCATION, filename)
        
    while not os.path.exists(full_path) and (time.time() - pre) < 8:
        time.sleep(0.125)
    
    if (time.time() - pre) >= 8:
        return "no help file found"
    
    return IFrame("/files/help_files/" + filename, "100%", 350)

def helpfile_in_path(name, path):
    try:
        dirpath, dirnames, filenames = os.walk(path).next()
    except StopIteration:
        return False
    
    for f in filenames:
        if f.startswith(name) and (f.endswith('.sthlp') or f.endswith('.hlp')):
            make_help(dirpath, f)
            return (f[:-6] if f.endswith('.sthlp') else f[:-4]) + ".html"
    
    return False
    
def help_html_exists(name):
    try:
        dirpath, dirnames, filenames = os.walk(HELP_HTML_LOCATION).next()
    except StopIteration:
        return False
        
    for f in filenames:
        if f.startswith(name) and f.endswith('.html'):
            return f
            
    return False
        
def get_help(name):
    global HELP_HTML_LOCATION, ADOPATH
    
    if name.endswith(".ado"):
        name = name[:-4]
    
    # first check to see if help html file already exists,
    # and if so, display it
    html_name = help_html_exists(name)
    if html_name:
        return display_help(html_name)
    
    # check if help file in ADOPATH
    for path in ADOPATH:
        html_name = helpfile_in_path(name, path)
        if html_name:
            return display_help(html_name)
            
    # check if help file in ADOPATH/first_letter
    first_letter = name[0]
    for path in ADOPATH:
        path += first_letter
        html_name = helpfile_in_path(name, path)
        if html_name:
            return display_help(html_name)
            
    return "no help file found for '{}'".format(name)

def is_image_cmd(cmd):
    cmd0 = cmd.split()[0]
    cmd0_len = len(cmd0)
    if cmd0 in image_cmds: return True
    if cmd0_len >= 2 and cmd0 == "scatter"[:cmd0_len]: return True
    if cmd0_len >= 4 and cmd0 == "histogram"[:cmd0_len]: return True
    return False

@magics_class
class MyMagics(Magics):
    @line_cell_magic
    def do(self, line, cell=None):
        global CURRENT_CMD
        cmd = line if cell is None else cell
        CURRENT_CMD = cmd
        first_word = cmd.split()[0]
        if first_word == "break":
            stataProg.UtilSetStataBreak()
            print_output()
        elif first_word == "help":
            help_info = get_help(cmd.split()[1])
            suppress_output()
            return help_info
        else:
            stataProg.UtilIsStataFreeEvent()
            rc = st_do("    " + cmd)
            if is_image_cmd(cmd):
                i = get_graph()
                return i
            else:
                print_output()

ip.register_magics(MyMagics)
output = suppress_output()



# modify run_cell to use do magic defined above
run_cell_orig = ip.run_cell
def run_cell_stata(
    raw_cell, store_history=False, silent=False, shell_futures=True
):
    m = pyre.match(raw_cell)
    if m is not None:
        raw_cell = raw_cell[m.end():]
    else:
        raw_cell = "%%do\n" + raw_cell
    run_cell_orig(raw_cell, store_history, silent, shell_futures)
ip.run_cell = run_cell_stata
    
    
def to_stata():
    ip.run_cell = run_cell_stata
    
def to_python():
    ip.run_cell = run_cell_orig
    
