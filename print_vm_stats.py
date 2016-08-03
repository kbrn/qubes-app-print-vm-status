#!/usr/bin/python2
# -*- coding: utf-8
import subprocess
import time
import sys
import re
import os

from qubes.qubes import QubesVmCollection
from qubes.qubes import QubesHost

vm_info_table = {}
pci_dev_names = {}
total_mem = 0
total_cpu = 0
qhost = QubesHost()

conky = False
conky_color = '#ffffff'
color_output = True
forever = True
outfd = sys.stdout
out_to_file = False

nonterminal = '├'
terminal = '└'
extender = '─'
ghost = '┊'
color_ghost = True

def vm_net_depth(name):
    info = vm_info_table[name]
    return 1 + len(info['pci_devs']) + sum(map(lambda n : (vm_net_depth(n) if visible(n) else 0), info['child_vms']))

def visible(name):
    info = vm_info_table[name]
    if(info['running'] == True):
        return True
    elif(True in map(lambda n : visible(n), info['child_vms'])):
        return True
    else:
        return False

def print_vm_info(name, nindent, parent_color, parent_connector, last_child):
    global conky
    global conky_color
    global color_output
    global forever
    global outfd
    global total_mem
    global total_cpu

    if(visible(name) == False):
        return

    cpu = vm_info_table[name]['cpu_usage']
    memory = vm_info_table[name]['memory']
    pcidevs = vm_info_table[name]['pci_devs']
    child_vms = vm_info_table[name]['child_vms']
    color = vm_info_table[name]['color']
    running = vm_info_table[name]['running']

    total_mem = total_mem + memory
    total_cpu = total_cpu + cpu

    colorreset = '\x1b[0m'

    if(conky == True):
        color = '${{color {:s}}}'.format(vm_info_table[name]['color'])
        colorreset = '${{color {:s}}}'.format(conky_color)

    if(color_output == False):
        color = ''
        colorreset = ''
        parent_color = ''

    connector = ''
    inheritance = ''
    displayname = name

    if(running == False):
        displayname = '{:s}(*)'.format(name)


    if(nindent > 0):
        last_child_connector = ''
        not_last_child_connector = ''
        if(color_ghost == True):
            not_last_child_connector = '{:s}{:s}{:s} '.format(parent_color, ghost, colorreset)
        else:
            not_last_child_connector = '{:s}{:s}{:s} '.format('', ghost, '')

        if(last_child):
            a = parent_connector + last_child_connector
            inheritance = a + '{trash:<{width}}'.format(trash = '', width = nindent/2 + 1)
            connector = '{:s}{:s}{:s}{:s}{:s}'.format(a, parent_color, terminal, extender, colorreset)
        else:
            a = parent_connector + '{:s}{:s}{:s}'.format(parent_color, nonterminal, colorreset)
            inheritance = parent_connector + not_last_child_connector
            connector = '{:s}{:s}{:s}{:s}'.format(a, parent_color, extender, colorreset)

    outfd.write('{:5d}M {:5.1f}% {:s}{:s}{:s}{:s}\n'.format(memory, cpu, connector, color, displayname, colorreset))

    if(len(child_vms) != 0 or len(pcidevs) != 0):
        corner = ''
        if(len(child_vms) != 0):
            corner = nonterminal
        else:
            corner = terminal
        indent = '{:s}{:s}{:s}{:s}{:s}'.format(inheritance, color, corner, extender, colorreset);
        if(len(pcidevs) != 0):
            for dev in pcidevs:
                extraspaces = 14 #for the stats we don't show on these lines
                padding = '{trash:<{width}}'.format(trash = '', width = extraspaces)
                outfd.write('{:s}{:s}{:s} ({:s})\n'.format(padding, indent, dev, pci_dev_names[dev]))
        if(len(child_vms) != 0):
            sorted_child_vms = sorted(child_vms, key = lambda vm: vm_net_depth(vm))
            sorted_child_vms = filter(lambda n: visible(n), sorted_child_vms)
            i = 0
            while(i < len(sorted_child_vms)):
                child_vm = sorted_child_vms[i]
                child_is_last = False
                if(i == len(sorted_child_vms) - 1):
                    child_is_last = True
                print_vm_info(child_vm, nindent + 2, color, inheritance, child_is_last)
                i = i+1

def print_vm_stats():
    global vm_info_table
    global out_to_file
    global total_mem
    global total_cpu

    qvm_collection = QubesVmCollection()
    qvm_collection.lock_db_for_reading()
    qvm_collection.load()
    qvm_collection.unlock_db()

    #get CPU usage (or try to, anyway) -- FIXME why does this take a whole fucking second?!
    qvm_collection.popitem() #remove Dom0 from collection
    (cur_time, cpu_usages) = qhost.measure_cpu_usage(qvm_collection)

    #get various stats per VM        
    for v in qvm_collection.values():
        info_table = {}
        #ipd.asd
        name = v.name
        color = v.label.name
        if(conky == False):
            if color == 'black': color = '\x1b[38;5;7m\x1b[48;5;232m'
            elif color == 'gray': color = '\x1b[38;5;232m\x1b[48;5;7m'
            elif color == 'purple': color = '\x1b[38;5;232m\x1b[48;5;13m'
            elif color == 'blue': color = '\x1b[38;5;232m\x1b[48;5;4m'
            elif color == 'green': color = '\x1b[38;5;232m\x1b[48;5;46m'
            elif color == 'yellow': color = '\x1b[38;5;232m\x1b[48;5;226m'
            elif color == 'orange': color = '\x1b[38;5;232m\x1b[48;5;3m'
            elif color == 'red': color = '\x1b[38;5;232m\x1b[48;5;160m'
        else:
            if color == 'black': color = '#333333' #so it isn't completely black
            elif color == 'gray': color = '#777975'
            elif color == 'purple': color = '#75507b'
            elif color == 'blue': color = '#3465a4'
            elif color == 'green': color = '#73d216'
            elif color == 'yellow': color = '#edd400'
            elif color == 'orange': color = '#f57900'
            elif color == 'red': color = '#cc0000'

        if(v.xid != -1):
            info_table['running'] = True
            info_table['pci_devs'] = v.pcidevs
            info_table['cpu_usage'] = round(cpu_usages[v.get_xid()]['cpu_usage'],1)
        else:
            info_table['running'] = False
            info_table['pci_devs'] = []
            info_table['cpu_usage'] = 0

        info_table['color'] = color
        info_table['memory'] = v.get_mem() / 1024

        info_table['netvm'] = ''
        if(v.netvm): info_table['netvm'] = v.netvm.name

        info_table['type'] = ''
        if(v.type == 'ProxyVM'): info_table['type'] = 'ProxyVM'
        if(v.type == 'NetVM'): info_table['type'] = 'NetVM'

        info_table['child_vms'] = []
        vm_info_table[name] = info_table

    #iterate through the table and set the 'child_vms' field
    for name, info_table in vm_info_table.iteritems():
        if(info_table['netvm'] != ''):
            my_netvm = info_table['netvm']
            vm_info_table[my_netvm]['child_vms'].append(name)

    #sort VMs by NetVM depth
    defer = []
    for name, info in vm_info_table.iteritems():
        if(info['netvm'] == ''):
            defer.append(name)

    info_order = sorted(defer, key = lambda vm: vm_net_depth(vm));

    #clear the screen:
    if(forever == True and out_to_file == False):
        sys.stdout.write('\x1b[0;0H\x1b[2J')

    #clear system stats before re-scan
    total_mem = 0
    total_cpu = 0

    #print VM stats
    for vm in info_order:
        print_vm_info(vm, 0, '', '', True);

    print_system_stats();
    vm_info_table = {};

def get_dom0_cpu():
    global total_cpu

    stat = subprocess.Popen(['cat', '/proc/stat'], stdout = subprocess.PIPE)
    for line in stat.stdout:
        fields = line.split()
        if 'cpu' not in fields[0]: continue
        if fields[0] != 'cpu': continue
        user = float(fields[1])
        #usernice = float(fields[2])
        usernice = 0
        system = float(fields[3])
        idle = float(fields[4])
        total = ((user + usernice + system) / (user + usernice + system + idle)) * 100
        total_cpu = total_cpu + total
        #sys.stdout.write('found {:f} usage\n'.format(total))

def print_system_stats():
    global total_mem
    global total_cpu
    connector = ''
    color = '\x1b[38;5;7m\x1b[48;5;232m'
    colorreset = '\x1b[0m'
    get_dom0_cpu()
    outfd.write('\n{:s}{:05d}M {:5.1f}% {:s}{:s}{:s}\n'.format(color, total_mem, total_cpu, connector, 'SYSTEM TOTAL', colorreset))
    return

def main():
    global conky_color
    global conky
    global color_output
    global forever
    global outfd
    global out_to_file

    outfile = ''
    out_to_file = False
    delay = 2

    #build PCI dev name dict
    cmd = subprocess.Popen(['/usr/sbin/lspci'], stdout = subprocess.PIPE)
    regexp = re.compile('([^:]*:[^.]*\.[^ ]*) ([^:]*):.*')
    for line in cmd.stdout:
        parts = regexp.match(line)
        pci_dev_names[parts.group(1)] = parts.group(2)

    #parse argv[]
    i = 0
    while(i < len(sys.argv)):
        arg = sys.argv[i]
        if(arg == 'color'):
            color_output = True
        elif(arg == 'nocolor'):
            color_output = False
        elif(arg == 'once'):
            forever = False
        elif(arg == 'forever'):
            forever = True
        elif(arg == 'conky'):
            conky = True
            i = i+1
            conky_color = sys.argv[i]
        elif(arg == 'outfile'):
            i = i+1
            outfile = sys.argv[i]
            out_to_file = True
            tmpfile = '/tmp/qubes-vm-stats'
        elif(arg == 'delay'):
            i = i+1
            delay = int(sys.argv[i]) - 1 #-1 because CPU usage takes ~1 second to get...
        i = i+1

    if(forever == True):
        while True:
            try:
                if(out_to_file == True):
                    outfd = open(tmpfile, 'w')

                print_vm_stats()

                if(out_to_file == True):
                    outfd.close()
                    os.rename(tmpfile, outfile)
            except:
                    pass

            time.sleep(delay)
    else:
        print_vm_stats()

main()
