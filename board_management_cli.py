#!/usr/bin/env python3

from __future__ import annotations
import cmd
import os
import subprocess
import argparse
from queue import Queue
import pickle
from functools import partial
import readline
import threading
import tkinter
import re
import traceback
import warnings
from typing import Callable, Iterable, Optional

from board_allocator import now, default_filename, BoardAllocator, FIG_DIR

#----------------------------------------------------------------------------------------
class FigViewer:
    def __init__(self, 
                 quit_event: threading.Event, 
                 refresh_interval: int = 500):
        self.refresh_interval = refresh_interval
        self.quit_event = quit_event
        self.root = tkinter.Tk()
        self.root.title('current node status')
        self.root.geometry("640x480")
        self.canvas = tkinter.Canvas(width=640, height=480)
        self.canvas.place(x=0, y=0)
        self.img = tkinter.PhotoImage(file=DEFAULT_NODE_STATUS_FIG)
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        self.canvas.create_image(canvas_width / 2, canvas_height / 2, image=self.img)

    ##-----------------------------------------------------------------------------------
    def mainloop(self):
        self.oneloop()
        self.root.mainloop()

    ##-----------------------------------------------------------------------------------
    def oneloop(self):
        if self.quit_event.is_set():
            self.root.destroy()
            return

        self.img = tkinter.PhotoImage(file=DEFAULT_NODE_STATUS_FIG)
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        self.canvas.create_image(canvas_width / 2, canvas_height / 2, image=self.img)
        self.root.after(self.refresh_interval, self.oneloop)

#----------------------------------------------------------------------------------------
def fig_view(quit_event: threading.Event):
    viewer = FigViewer(quit_event)
    viewer.mainloop()

#----------------------------------------------------------------------------------------
def return_empty_list(_):
    return []

#----------------------------------------------------------------------------------------
class Arg:
    def __init__(self, 
                 nargs: int | float = 0, 
                 func: Callable[..., list[str]] = return_empty_list):
        self.nargs = nargs
        self.func = func

SAVE_DIR = 'save'
DEFAULT_NODE_STATUS_FIG = os.path.join(FIG_DIR, 'current.png')
#----------------------------------------------------------------------------------------
class BoardManagementCLI(cmd.Cmd):
    intro = 'Board Management CLI'
    prompt = '>> '
    __SHOW_APPS_COND_VARS = ['app_id']
    __SHOW_NODES_COND_VARS = ['app_id', 'vNode_id', 'rNode_id']
    __SHOW_FLOWS_COND_VARS = ['app_id', 'flow_id', 'slot_id']
    # sample code
    arg3_choices = ['alpha', 'beta', 'gamma']
    

    ##-----------------------------------------------------------------------------------
    def __init__(self):
        super().__init__()
        self.ba: Optional[BoardAllocator] = None
        self.fig_thread: Optional[threading.Thread] = None
        self.fig_quit_event = threading.Event()
        self.is_saved = True
        readline.set_completer_delims(' \t\n`~!@#$%^&*()=+[{]}\\|;:\'",<>/?')
        if not os.path.isdir(SAVE_DIR):
            os.mkdir(SAVE_DIR)
        if not os.path.isdir(FIG_DIR):
            os.mkdir(FIG_DIR)
    
    ##-----------------------------------------------------------------------------------
    def do_wipe(self, line):
        parser = argparse.ArgumentParser(prog="wipe", 
                                         description='wipe the current allocator')
        parser.add_argument('-f', '--force', action='store_true', help='Forcibly wipe')

        try:
            args = parser.parse_args(args=line.split())
        except SystemExit:
            return None

        if (self.ba is not None) and (not args.force):
            print("An allocator exists.")
            ans = input("Do you want to wipe it? [y/n]: ")
            while ans != 'y' and ans != 'n':
                ans = input("Please input y or n: ")
            if ans == 'n':
                return None
            if not self.is_saved:
                ans = input("Do you save the current allocator? [y/n]: ")
                while ans != 'y' and ans != 'n':
                    ans = input("Please input y or n: ")
                if ans == 'y':
                    self.do_save()
        
        self.ba = None
        self.is_saved = True
    
    ##-----------------------------------------------------------------------------------
    def complete_wipe(self, text, line, begidx, endidx):
        arg_name2Arg = {'-f': Arg(0),
                        '--force': Arg(0)}
        return self._argparse_completion(text, line, begidx, endidx, arg_name2Arg)

    ##-----------------------------------------------------------------------------------
    def do_init(self, line):
        parser = argparse.ArgumentParser(prog="init", 
                                         description='initialization your allocator')
        parser.add_argument('topo_file', nargs='?', default='fic-topo-file-cross.txt', 
                            help='topology file')
        parser.add_argument('-f', '--force', action='store_true', 
                            help='Forcibly initialize')

        try:
            args = parser.parse_args(args=line.split())
        except SystemExit:
            return None

        if (self.ba is not None) and (not args.force):
            print("Other allocator has already been loaded.")
            ans = input("Wipe the currrent allocator and set up a new one? [y/n]: ")
            while ans != 'y' and ans != 'n':
                ans = input("Please input y or n: ")
            if ans == 'n':
                return None
            if not self.is_saved:
                ans = input("Do you save the current allocator? [y/n]: ")
                while ans != 'y' and ans != 'n':
                    ans = input("Please input y or n: ")
                if ans == 'y':
                    self.do_save()
        
        self.ba = BoardAllocator(args.topo_file)
        self.ba.draw_current_node_status(DEFAULT_NODE_STATUS_FIG)
        self.is_saved = True
    
    ##-----------------------------------------------------------------------------------
    def complete_init(self, text, line, begidx, endidx):
        arg_name2Arg = {'topo_file': Arg(1, self._filename_completion)}
        return self._argparse_completion(text, line, begidx, endidx, arg_name2Arg)
    
    ##-----------------------------------------------------------------------------------
    def do_save(self, line=""):
        parser = argparse.ArgumentParser(prog="save", description='save the allocator')
        parser.add_argument('-o', '--output', default=None, help='output file')
        parser.add_argument('-f', '--force', action='store_true', 
                            help='Forcibly overwrite')
    
        try:
            args = parser.parse_args(args=line.split())
        except SystemExit:
            return None
        
        if args.output is None:
            output_file = os.path.join(SAVE_DIR, (default_filename() + '.pickle'))
        else:
            output_file = args.output
        
        if os.path.exists(output_file) and (not args.force):
            print("The file already exists.")
            ans = input("Do you want to overwrite it? [y/n]: ")
            while ans != 'y' and ans != 'n':
                ans = input("Please input y or n: ")
            if ans == 'n':
                print("Please try again.")
                return None

        self.is_saved = True
        with open(output_file, 'wb') as f:
            pickle.dump(self.ba, f, protocol=pickle.HIGHEST_PROTOCOL)
        print("Save allocator to {}".format(os.path.abspath(output_file)))

    ##-----------------------------------------------------------------------------------
    def complete_save(self, text, line, begidx, endidx):
        arg_name2Arg = {'-o': Arg(1, self._filename_completion),
                        '--output': Arg(1, self._filename_completion),
                        '-f': Arg(0),
                        '--force': Arg(0)}
        return self._argparse_completion(text, line, begidx, endidx, arg_name2Arg)
    
    ##-----------------------------------------------------------------------------------
    def do_add_app(self, line):
        parser = argparse.ArgumentParser(prog="addapp", description='add applications')
        parser.add_argument('comm_files', nargs='+', 
                            help='communication pattern file(s)')
        
        if self.ba is None:
            print("There is no allocator. Please execute 'init' or 'load' command.")
            return None
        
        try:
            args = parser.parse_args(args=line.split())
        except SystemExit:
            return None
        
        for f in args.comm_files:
            if self.ba.load_app(f):
                print("{} successfully added.".format(f))
                self.is_saved = False
            else:
                print("Failed to add {}: too many boards.".format(f))
    
    ##-----------------------------------------------------------------------------------
    def complete_add_app(self, text, line, begidx, endidx):
        arg_name2Arg = {'comm_files': Arg(float('inf'), self._filename_completion)}
        return self._argparse_completion(text, line, begidx, endidx, arg_name2Arg)
    
    ##-----------------------------------------------------------------------------------
    def do_rm_app(self, line):
        parser = argparse.ArgumentParser(prog="rmapp", description='remove applications')
        parser.add_argument('app_id', nargs='*', type=int,
                            help='app_id(s) you want to remove')
        parser.add_argument('--all', action='store_true', help='remove all applications')
        
        if self.ba is None:
            print("There is no allocator. Please execute 'init' or 'load' command.")
            return None

        try:
            args = parser.parse_args(args=line.split())
        except SystemExit:
            return None

        if args.all:
            for app_id in self.ba.app_id2vitrualizer.keys():
                self.ba.remove_app(app_id)
                self.is_saved = False
        elif args.app_id == []:
            print("No application to be deleted was specified.")
        else:
            for app_id in set(args.app_id):
                try:
                    self.ba.remove_app(app_id)
                except ValueError as e:
                    for s in traceback.format_exception_only(type(e), e):
                        print(s.rstrip('\n'))
                else:
                    self.is_saved = False

        self.ba.draw_current_node_status(DEFAULT_NODE_STATUS_FIG)
    
    ##-----------------------------------------------------------------------------------
    def complete_rm_app(self, text, line, begidx, endidx):
        completor = partial(self._completion_by_iterable, 
                            iterable=self.ba.app_id2vitrualizer.keys())
        arg_name2Arg = {'app_id': Arg(float('inf'), completor),
                        '--all': Arg(0)}
        return self._argparse_completion(text, line, begidx, endidx, arg_name2Arg)
    
    ##-----------------------------------------------------------------------------------
    def do_status(self, line):
        parser = argparse.ArgumentParser(prog="status", 
                                         description='get the status of your allocator')
        parser.add_argument('-f', '--full', action='store_true', 
                            help='display full status')

        if self.ba is None:
            print("There is no allocator. Please execute 'init' or 'load' command.")
            return None

        try:
            args = parser.parse_args(args=line.split())
        except SystemExit:
            return None

        self.ba.print_result(args.full)
    
    ##-----------------------------------------------------------------------------------
    def complete_status(self, text, line, begidx, endidx):
        arg_name2Arg = {'-f': Arg(0),
                        '--full': Arg(0)}
        return self._argparse_completion(text, line, begidx, endidx, arg_name2Arg)
    
    ##-----------------------------------------------------------------------------------
    def do_twoopt(self, line):
        parser = argparse.ArgumentParser(prog="twoopt", description='execute 2-opt')
        parser.add_argument('-s', default=0, type=float, 
                            help='execution_time += int(s)')
        parser.add_argument('-m', default=0, type=float, 
                            help='execution_time += 60 * int(m)')
        parser.add_argument('-ho', default=0, type=float, 
                            help='execution_time += 3600 * int(ho)')

        if self.ba is None:
            print("There is no allocator. Please execute 'init' or 'load' command.")
            return None

        try:
            args = parser.parse_args(args=line.split())
        except SystemExit:
            return None
        
        execution_time = args.s + 60 * args.m + 3600 * args.ho
        if (execution_time <= 0):
            print("Total execution time must be greater than 0 second.")
            return

        self.ba.two_opt(execution_time)
        self.ba.draw_current_node_status(DEFAULT_NODE_STATUS_FIG)
        self.is_saved = False
    
    ##-----------------------------------------------------------------------------------
    def complete_twoopt(self, text, line, begidx, endidx):
        arg_name2Arg = {'-s': Arg(1),
                        '-m': Arg(1), 
                        '-ho': Arg(1)}
        return self._argparse_completion(text, line, begidx, endidx, arg_name2Arg)
    
    ##-----------------------------------------------------------------------------------
    def do_alns(self, line):
        parser = argparse.ArgumentParser(prog="alns", description='execute alns')
        parser.add_argument('-s', default=0, type=float, 
                            help='execution_time += int(s)')
        parser.add_argument('-m', default=0, type=float, 
                            help='execution_time += 60 * int(m)')
        parser.add_argument('-ho', default=0, type=float, 
                            help='execution_time += 3600 * int(ho)')

        if self.ba is None:
            print("There is no allocator. Please execute 'init' or 'load' command.")
            return None

        try:
            args = parser.parse_args(args=line.split())
        except SystemExit:
            return None
        
        execution_time = args.s + 60 * args.m + 3600 * args.ho
        if (execution_time <= 0):
            print("Total execution time must be greater than 0 second.")
            return

        self.ba.alns(execution_time)
        self.ba.draw_current_node_status(DEFAULT_NODE_STATUS_FIG)
        self.is_saved = False
    
    ##-----------------------------------------------------------------------------------
    def complete_alns(self, text, line, begidx, endidx):
        arg_name2Arg = {'-s': Arg(1),
                        '-m': Arg(1), 
                        '-ho': Arg(1)}
        return self._argparse_completion(text, line, begidx, endidx, arg_name2Arg)

    ##-----------------------------------------------------------------------------------
    def do_nsga2(self, line):
        parser = argparse.ArgumentParser(prog="nsga2", description='execute nsga2')
        parser.add_argument('-s', default=0, type=float, 
                            help='execution_time += int(s)')
        parser.add_argument('-m', default=0, type=float, 
                            help='execution_time += 60 * int(m)')
        parser.add_argument('-ho', default=0, type=float, 
                            help='execution_time += 3600 * int(ho)')
        parser.add_argument('-p', default=1, type=int, help='# of processes to use')

        if self.ba is None:
            print("There is no allocator. Please execute 'init' or 'load' command.")
            return None

        try:
            args = parser.parse_args(args=line.split())
        except SystemExit:
            return None
        
        execution_time = args.s + 60 * args.m + 3600 * args.ho
        if (execution_time <= 0):
            print("Total execution time must be greater than 0 second.")
            return
        
        try: 
            warnings.filterwarnings(action='ignore', 
                                    category=RuntimeWarning, module=r'.*creator')
            hof = self.ba.nsga2(execution_time, args.p)
            warnings.resetwarnings()
        except ValueError as e:
            for s in traceback.format_exception_only(type(e), e):
                print(s.rstrip('\n'))
        ## self.ba.select_from_hof(hof)
        self.ba.draw_current_node_status(DEFAULT_NODE_STATUS_FIG)
        self.is_saved = False
    
    ##-----------------------------------------------------------------------------------
    def complete_nsga2(self, text, line, begidx, endidx):
        arg_name2Arg = {'-s': Arg(1),
                        '-m': Arg(1), 
                        '-ho': Arg(1),
                        '-p': Arg(1)}
        return self._argparse_completion(text, line, begidx, endidx, arg_name2Arg)
    
    ##-----------------------------------------------------------------------------------
    def do_spea2(self, line):
        parser = argparse.ArgumentParser(prog="spea2", description='execute spea2')
        parser.add_argument('-s', default=0, type=float, 
                            help='execution_time += int(s)')
        parser.add_argument('-m', default=0, type=float, 
                            help='execution_time += 60 * int(m)')
        parser.add_argument('-ho', default=0, type=float, 
                            help='execution_time += 3600 * int(ho)')
        parser.add_argument('-p', default=1, type=int, help='# of processes to use')

        if self.ba is None:
            print("There is no allocator. Please execute 'init' or 'load' command.")
            return None

        try:
            args = parser.parse_args(args=line.split())
        except SystemExit:
            return None
        
        execution_time = args.s + 60 * args.m + 3600 * args.ho
        if (execution_time <= 0):
            print("Total execution time must be greater than 0 second.")
            return
        
        try:
            warnings.filterwarnings(action='ignore', 
                                    category=RuntimeWarning, module=r'.*creator')
            hof = self.ba.spea2(execution_time, args.p)
            warnings.resetwarnings()
        except ValueError as e:
            for s in traceback.format_exception_only(type(e), e):
                print(s.rstrip('\n'))
        ## self.ba.select_from_hof(hof)
        self.ba.draw_current_node_status(DEFAULT_NODE_STATUS_FIG)
        self.is_saved = False
    
    ##-----------------------------------------------------------------------------------
    def complete_spea2(self, text, line, begidx, endidx):
        arg_name2Arg = {'-s': Arg(1),
                        '-m': Arg(1), 
                        '-ho': Arg(1),
                        '-p': Arg(1)}
        return self._argparse_completion(text, line, begidx, endidx, arg_name2Arg)
    
    ##-----------------------------------------------------------------------------------
    def do_ncga(self, line):
        parser = argparse.ArgumentParser(prog="ncga", description='execute ncga')
        parser.add_argument('-s', default=0, type=float, 
                            help='execution_time += int(s)')
        parser.add_argument('-m', default=0, type=float, 
                            help='execution_time += 60 * int(m)')
        parser.add_argument('-ho', default=0, type=float, 
                            help='execution_time += 3600 * int(ho)')
        parser.add_argument('-p', help='# of processes to use', default=1, type=int)

        if self.ba is None:
            print("There is no allocator. Please execute 'init'or 'load' command.")
            return None

        try:
            args = parser.parse_args(args=line.split())
        except SystemExit:
            return None
        
        execution_time = args.s + 60 * args.m + 3600 * args.ho
        if (execution_time <= 0):
            print("Total execution time must be greater than 0 second.")
            return
        
        try:
            warnings.filterwarnings(action='ignore', 
                                    category=RuntimeWarning, module=r'.*creator')
            hof = self.ba.ncga(execution_time, args.p)
            warnings.resetwarnings()
        except ValueError as e:
            for s in traceback.format_exception_only(type(e), e):
                print(s.rstrip('\n'))
        ## self.ba.select_from_hof(hof)
        self.ba.draw_current_node_status(DEFAULT_NODE_STATUS_FIG)
        self.is_saved = False
    
    ##-----------------------------------------------------------------------------------
    def complete_ncga(self, text, line, begidx, endidx):
        arg_name2Arg = {'-s': Arg(1),
                        '-m': Arg(1), 
                        '-ho': Arg(1),
                        '-p': Arg(1)}
        return self._argparse_completion(text, line, begidx, endidx, arg_name2Arg)

    ##-----------------------------------------------------------------------------------
    def do_show_apps(self, line):
        parser = argparse.ArgumentParser(prog="show_apps", 
                                         description='show applications')
        parser.add_argument('-w', '--where', nargs='*', default=[], 
                            help='the condition of items to display')

        if self.ba is None:
            print("There is no allocator. Please execute 'init' or 'load' command.")
            return None
        
        try:
            args = parser.parse_args(args=line.split())
        except SystemExit:
            return None

        if args.where == []:
            self.ba.show_apps()
        else:
            func = self._make_lambda(args.where, self.__SHOW_APPS_COND_VARS)
            if func is None:
                return None
            self.ba.show_apps(key=func)

    ##-----------------------------------------------------------------------------------
    def complete_show_apps(self, text, line, begidx, endidx):
        completor = partial(self._completion_by_iterable, 
                            iterable=self.__SHOW_APPS_COND_VARS,
                            is_expr=True)
        arg_name2Arg = {'--where': Arg(float('inf'), completor), 
                        '-w': Arg(float('inf'), completor)}
        return self._argparse_completion(text, line, begidx, endidx, arg_name2Arg)
    
    ##-----------------------------------------------------------------------------------
    def do_show_nodes(self, line):
        parser = argparse.ArgumentParser(prog="show_nodes", description='show nodes')
        parser.add_argument('-w', '--where', nargs='*', default=[], 
                            help='the condition of items to display')

        if self.ba is None:
            print("There is no allocator. Please execute 'init' or 'load' command.")
            return None
        
        try:
            args = parser.parse_args(args=line.split())
        except SystemExit:
            return None

        if args.where == []:
            self.ba.show_nodes()
        else:
            func = self._make_lambda(args.where, self.__SHOW_NODES_COND_VARS)
            if func is None:
                return None
            self.ba.show_nodes(key=func)

    ##-----------------------------------------------------------------------------------
    def complete_show_nodes(self, text, line, begidx, endidx):
        completor = partial(self._completion_by_iterable, 
                            iterable=self.__SHOW_NODES_COND_VARS,
                            is_expr=True)
        arg_name2Arg = {'--where': Arg(float('inf'), completor), 
                        '-w': Arg(float('inf'), completor)}
        return self._argparse_completion(text, line, begidx, endidx, arg_name2Arg)
    
    ##-----------------------------------------------------------------------------------
    def do_show_flows(self, line):
        parser = argparse.ArgumentParser(prog="show_flows", description='show flows')
        parser.add_argument('-w', '--where', nargs='*', default=[], 
                            help='the condition of items to display')

        if self.ba is None:
            print("There is no allocator. Please execute 'init' or 'load' command.")
            return None
        
        try:
            args = parser.parse_args(args=line.split())
        except SystemExit:
            return None

        if args.where == []:
            self.ba.show_flows()
        else:
            func = self._make_lambda(args.where, self.__SHOW_FLOWS_COND_VARS)
            if func is None:
                return None
            self.ba.show_flows(key=func)

    ##-----------------------------------------------------------------------------------
    def complete_show_flows(self, text, line, begidx, endidx):
        completor = partial(self._completion_by_iterable, 
                            iterable=self.__SHOW_FLOWS_COND_VARS, 
                            is_expr=True)
        arg_name2Arg = {'--where': Arg(float('inf'), completor), 
                        '-w': Arg(float('inf'), completor)}
        return self._argparse_completion(text, line, begidx, endidx, arg_name2Arg)

    ##-----------------------------------------------------------------------------------
    def do_show_fig(self, line):
        parser = argparse.ArgumentParser(prog="show_fig", 
                                    description='show the current node status figure')
        parser.add_argument('--off', action='store_true', help='disable GUI')

        try:
            args = parser.parse_args(args=line.split())
        except SystemExit:
            return None
        
        if args.off:
            self.fig_thread = None
            self.fig_quit_event.set()
            return None

        if (self.fig_thread is None) or (not self.fig_thread.is_alive()):
            if self.ba is None:
                print("There is no allocator. Please execute 'init' or 'load' command.")
                return None
            self.fig_quit_event.clear()
            self.fig_thread = threading.Thread(target=fig_view, args=(self.fig_quit_event,))
            self.fig_thread.start()
        else:
            print("Other GUI is running.")
    
    ##-----------------------------------------------------------------------------------
    def complete_show_fig(self, text, line, begidx, endidx):
        arg_name2Arg = {'--off': Arg(0)}
        return self._argparse_completion(text, line, begidx, endidx, arg_name2Arg)

    ##-----------------------------------------------------------------------------------
    # sample code of command
    def do_command(self, line):
        parser = argparse.ArgumentParser(prog="command", description='command test')
        parser.add_argument('arg1', help='a required file')
        parser.add_argument('arg2', nargs='+', help='required directories')
        parser.add_argument('--arg3', choices=self.arg3_choices, help='choose one of them')
        parser.add_argument('--arg4', action='store_true', help='flag')
        parser.add_argument('--arg5', nargs='+', help='multiple args')

        try:
            args = parser.parse_args(args=line.split())
        except SystemExit:
            return None

        print("executed: command {a1} {a2} --arg3 {a3} --arg4 {a4} --arg5 {a5}".format(
              a1=args.arg1, a2=args.arg2, a3=args.arg3, a4=args.arg4, a5=args.arg5))

    ##-----------------------------------------------------------------------------------
    # sample code of complition if command
    def complete_command(self, text, line, begidx, endidx):
        # inform the argument string nargs and function
        arg_name2Arg = {'arg1': Arg(1, self._filename_completion), 
                     'arg2': Arg(float('inf'), self._dirname_completion), 
                     '--arg3': Arg(1, partial(self._completion_by_iterable, 
                                              iterable=self.arg3_choices)), 
                     '--arg4': Arg(0), 
                     '--arg5': Arg(float('inf'), self._filename_completion)}

        return self._argparse_completion(text, line, begidx, endidx, arg_name2Arg)

    ##-----------------------------------------------------------------------------------
    def do_pwd(self, line):
        print(os.getcwd())

    ##-----------------------------------------------------------------------------------
    def do_ls(self, line):
        args = line.split()
        subprocess.run(['ls'] + args)

    ##-----------------------------------------------------------------------------------
    def complete_ls(self, text, line, begidx, endidx):
        args = line.split()
        if line[-1] == ' ':
            args.append(text)
        if args[-1].startswith('-'):
            return []
        else:
            return self._filename_completion(args[-1])

    ##-----------------------------------------------------------------------------------
    def do_time(self, _):
        print(now())

    ##-----------------------------------------------------------------------------------
    def do_exit(self, line):
        parser = argparse.ArgumentParser(prog="exit", description='exit this CLI')
        parser.add_argument('-i', '--inform', action='store_true', 
                            help='inform if the current allocator is not saved')
        
        try:
            args = parser.parse_args(args=line.split())
        except SystemExit:
            return None

        if not self.is_saved and args.inform:
            print("The current allocator is not saved.")
            ans = input("Do you save the current allocator? [y/n]: ")
            while ans != 'y' and ans != 'n':
                ans = input("Please input y or n: ")
            if ans == 'y':
                self.do_save()
            else:
                ans = input("Do you want to exit without serving? [y/n]: ")
                while ans != 'y' and ans != 'n':
                    ans = input("Please input y or n: ")
                if ans == 'n':
                    return None
        self.fig_quit_event.set()
        return True
    
    ##-----------------------------------------------------------------------------------
    def complete_exit(self, text, line, begidx, endidx):
        arg_name2Arg = {'-i': Arg(0),
                        '--inform': Arg(0)}
        return self._argparse_completion(text, line, begidx, endidx, arg_name2Arg)

    ##-----------------------------------------------------------------------------------
    @staticmethod
    def _argparse_completion(text: str, line: str, begidx, endidx, 
                             arg_name2Arg: dict[str, Arg]) -> list[str]:
        '''
        Note: 
            arg in arg_name2Arg[option].func(arg) represents the string after the last 
            blank in the line containing the string to be completed. Therefore, arg and 
            text are generally different.
            example:
                line = 'command pareant/child'
                text = 'child'
                arg =  'parent/child'
            
            Specifying a character starting with '-', such as '-1' or '-arg', 
            as an element in the list of return values for arg_name2Arg[option].func(arg)
            may cause unintended behavior.
        '''
        option_set = {a for a in arg_name2Arg.keys() if a.startswith('-')}
        required_args = [a for a in arg_name2Arg.keys() if not a.startswith('-')]
        required_args_q = Queue()
        for elm in required_args:
            required_args_q.put(elm)

        args = line.split()
        if line[-1] == ' ':
            args.append(text)

        option = None
        cnt = 0
        for i, arg in enumerate(args):
            if i == 0:
                continue
            elif arg in option_set:
                option = arg
                cnt = 0
            
            if (i == len(args) - 1):
                if arg.startswith('--'):
                    return [option_name + ' ' 
                            for option_name in option_set 
                            if option_name.startswith(args[-1])]
                elif arg.startswith('-') and cnt == 0:
                    candidates = [option_name + ' ' 
                                  for option_name in option_set 
                                  if option_name.startswith(args[-1]) 
                                  and (not option_name.startswith('--'))]
                    if len(candidates) > 0:
                        return candidates

            if option is None:
                if required_args_q.empty():
                    return []
                option = required_args_q.get()
                cnt = 1

            if (i == len(args) - 1) and cnt != 0:
                try:
                    return arg_name2Arg[option].func(arg)
                except KeyError:
                    return []
            
            if (option is None) or (cnt >= arg_name2Arg[option].nargs):
                option = None
                cnt = 0
            else: 
                cnt += 1

        return []

    ##-----------------------------------------------------------------------------------
    @staticmethod
    def _filename_completion(path: str = './') -> list[str]:
        dirname, filename = os.path.split(path)
        if dirname == '':
            dirname = './'

        ls_list = ['./', '../']

        with os.scandir(dirname) as scan_list:
            ls_list += [f.name + os.sep if f.is_dir() else f.name + ' ' 
                        for f in scan_list]

        if filename == '':
            return ls_list
        else:
            return [f for f in ls_list if f.startswith(filename)]

    ##-----------------------------------------------------------------------------------
    @staticmethod
    def _dirname_completion(path: str = './') -> list[str]:
        dirname, filename = os.path.split(path)
        if dirname == '':
            dirname = './'

        ls_list = ['./', '../']

        with os.scandir(dirname) as scan_list:
            ls_list += [f.name + os.sep for f in scan_list if f.is_dir()]

        if filename == '':
            return ls_list
        else:
            return [f for f in ls_list if f.startswith(filename)]

    ##-----------------------------------------------------------------------------------
    @staticmethod
    def _completion_by_iterable(arg: str, 
                                iterable: Iterable, 
                                is_expr: bool = False
                                ) -> list[str]:
        '''
        arg: a string
        iterable: an iterable object of string
        is_expr: whether arg is part of an expression or not
        '''
        if is_expr:
            base_pattern = '\(|\)|\[|\]|\{|\}|\+|\*\*|\*|\/\/|\||\/|\%|\~|\&|\,|\^'\
                           '|\=\=|\!\=|\<\=|\>\=|\<\<|\<|\>\>|\>|\`|\!|\@|\#|\$|\\|\;'\
                           '|\:|\'|\"|\?'
            pattern = re.compile(base_pattern)
            line = arg
            arg = pattern.split(arg)[-1]
            if not line.endswith(arg):
                return []

            if arg == '':
                return [str(elm) + ' ' for elm in iterable]
            else:
                return [str(elm) + ' ' for elm in iterable if str(elm).startswith(arg)]
            
        else:
            if arg == '':
                return [str(elm) + ' ' for elm in iterable]
            else:
                return [str(elm) + ' ' for elm in iterable if str(elm).startswith(arg)]
    
    ##-----------------------------------------------------------------------------------
    @staticmethod
    def _make_condition(cond_str_list: list[str], argument_strs: Iterable[str]) -> str:
        base_pattern = '\d*\.\d+|\d+\.\d*|\d+|\(|\)|\[|\]|\{|\}|\+|\-|\*\*|\*|\/\/|\|'\
                       '|\/|\%|\~|\&|\,|\^|\=\=|\!\=|\<\=|\>\=|\<\<|\<|\>\>|\>|is|not'\
                       '|in|and|or|not|if|else|None'
        pattern_str = '|'.join([base_pattern] + argument_strs)
        pattern = re.compile(pattern_str)

        print(cond_str_list)
        
        cond = ''
        for text in cond_str_list:
            while text != '':
                match_obj = pattern.match(text)
                if match_obj is None:
                    raise SyntaxError("'{}' is an unavailable expression.".format(text))
                cond += match_obj.group()
                text = text[match_obj.end():]
            cond += ' '
        
        return cond

    ##-----------------------------------------------------------------------------------
    @classmethod
    def _make_lambda(cls, 
                     args: list[str], 
                     acceptable_variables: Iterable[str]
                     ) -> Callable[..., bool] | None:
        
        if len(acceptable_variables) == 0:
            raise ValueError("No argument for lambda function")

        try:
            cond = cls._make_condition(args, acceptable_variables)
        except SyntaxError as e:
            for s in traceback.format_exception_only(type(e), e):
                print(s.rstrip('\n'))
            return None

        header = 'lambda ' + ', '.join(acceptable_variables) + ': '
        try:
            func = eval(header + cond)
        except SyntaxError as e:
            badline = e.text
            offset = e.offset
            cond_offset = len(header)
            err_strs = traceback.format_exception_only(type(e), e)
            n = 1
            if badline is not None:
                print(err_strs[n][4 + cond_offset:].rstrip('\n'))
                n += 1
                if offset is not None:
                    print(err_strs[n][4 + cond_offset:].rstrip('\n'))
                    n += 1
            print(err_strs[n].rstrip('\n'))
            return None
        return func

    ##-----------------------------------------------------------------------------------
    # overridden method
    def completenames(self, text, *ignored):
        dotext = 'do_'+text
        return [a[3:] + ' ' for a in self.get_names() if a.startswith(dotext)]

    ##-----------------------------------------------------------------------------------
    # overridden method
    def emptyline(self):
        pass

#----------------------------------------------------------------------------------------
if __name__ == '__main__':
    shell = BoardManagementCLI()
    #print(shell.complete_command('', 'command --arg3 alpha ', 0, 0))
    shell.cmdloop()
