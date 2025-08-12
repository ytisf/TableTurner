#!/usr/bin/env python3

import sys
import os
import curses
from pathlib import Path
from colorama import Fore, Style, init
from sql_parser_logic.SqlParserLogic import SqlParser

# Initialize colorama
init(autoreset=True)

class CursesTableSelector:
    def __init__(self, stdscr, tables, filename):
        self.stdscr = stdscr
        self.tables = tables
        self.filename = filename
        self.selected = set()
        self.current_pos = 0
        self.scroll_pos = 0
        
        # Sort tables to prioritize common ones
        iwant = ["account", "member", "user", "admins", "clients", "customers", "skype", "customer_entity"]
        self.tables.sort()
        upfirst = [x for x in self.tables if any(y in x.lower() for y in iwant)]
        self.choices = sorted(set(upfirst + self.tables), key=(upfirst + self.tables).index)

    def run(self):
        """Main loop to run the TUI."""
        curses.curs_set(0)
        self.stdscr.nodelay(0)
        self.stdscr.timeout(-1)

        while True:
            self.draw()
            key = self.stdscr.getch()

            if key == curses.KEY_UP:
                self.current_pos = max(0, self.current_pos - 1)
                if self.current_pos < self.scroll_pos:
                    self.scroll_pos = self.current_pos
            elif key == curses.KEY_DOWN:
                self.current_pos = min(len(self.choices) - 1, self.current_pos + 1)
                h, _ = self.stdscr.getmaxyx()
                if self.current_pos >= self.scroll_pos + h - 5:
                    self.scroll_pos = self.current_pos - (h - 5) + 1
            elif key == ord(' '):
                table = self.choices[self.current_pos]
                if table in self.selected:
                    self.selected.remove(table)
                else:
                    self.selected.add(table)
            elif key == ord('\n'):
                return list(self.selected)
            elif key == 27:  # ESC key
                return []

    def draw(self):
        """Draws the UI components on the screen."""
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        # Header
        title = f"Found {len(self.choices)} tables in {Path(self.filename).name}"
        instructions = "Up/Down: Navigate | Space: Select/Deselect | Enter: Confirm | ESC: Quit"
        self.stdscr.addstr(0, 1, title, curses.A_BOLD)
        self.stdscr.addstr(1, 1, instructions)
        
        # Separator
        self.stdscr.hline(2, 1, curses.ACS_HLINE, w - 2)

        # Display table list
        for i in range(h - 5):
            list_index = self.scroll_pos + i
            if list_index >= len(self.choices):
                break
            
            table = self.choices[list_index]
            prefix = "[x]" if table in self.selected else "[ ]"
            display_str = f"{prefix} {table}"
            
            if list_index == self.current_pos:
                self.stdscr.addstr(i + 4, 1, display_str, curses.A_REVERSE)
            else:
                self.stdscr.addstr(i + 4, 1, display_str)

        self.stdscr.refresh()

def tableSelectTUI(stdscr, tables, filename):
    """Wrapper to run the CursesTableSelector."""
    selector = CursesTableSelector(stdscr, tables, filename)
    return selector.run()

def sqlconverter_tui(filepath, dumpall=False):
    """Main TUI conversion logic."""
    # Pass the `dumpall` flag to the parser to control tqdm's output
    parser = SqlParser(filepath, show_progress=(dumpall))
    tables = parser.build_index()

    if not tables:
        print("Could not find any tables in the file.")
        return

    tablechoices = []
    if dumpall:
        tablechoices = tables
    else:
        # This will now be called correctly without interference
        tablechoices = curses.wrapper(tableSelectTUI, tables, filepath)

    if tablechoices:
        print(f"Extracting {len(tablechoices)} selected tables...")
        for table in tablechoices:
            try:
                parser.process_table(table)
            except Exception as e:
                print(f"{Fore.RED}Error processing table {table}: {e}")
    else:
        print("No tables selected. Exiting.")

def main():
    import argparse
    
    banner = f"""{Fore.CYAN}
                       _____  ____  _      _____                               
                      / ____|/ __ \| |    |  __ \                          _   
                     | (___ | |  | | |    | |__) |_ _ _ __ ___  ___ _ __ _| |_ 
                      \___ \| |  | | |    |  ___/ _` | '__/ __|/ _ \ '__|_   _|
                      ____) | |__| | |____| |  | (_| | |  \__ \  __/ |    |_|  
                     |_____/ \__\_\______|_|   \__,_|_|  |___/\___|_|         
                                                           
            {Style.RESET_ALL}Original by:{Fore.CYAN} Matteo Tomasini (citcheese){Style.RESET_ALL}
            {Style.RESET_ALL}Modified by:{Fore.CYAN} ytisf {Style.RESET_ALL}
            {Style.BRIGHT}TUI Version{Style.RESET_ALL}

            {Style.BRIGHT}        SQLParser+ (TUI) - Convert SQL dumps to CSVs!{Style.RESET_ALL}
    {Fore.CYAN}_____________________________________________________________________________{Style.RESET_ALL}
    """
    print(banner + "\n")


    parser = argparse.ArgumentParser()
    parser.add_argument('sqlextract', help="Path to the SQL file to process.")
    parser.add_argument('--dumpall', '-d', action='store_true', help="Grab and convert every table without showing the selector.")
    
    args = parser.parse_args()

    if os.path.isfile(args.sqlextract):
        sqlconverter_tui(args.sqlextract, dumpall=args.dumpall)
    else:
        print(f"{Fore.RED}Error: File not found at '{args.sqlextract}'")

if __name__ == '__main__':
    main()