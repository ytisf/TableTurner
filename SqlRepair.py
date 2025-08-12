#!/usr/bin/env python3

import csv
import re
import sys
from pathlib import Path
import argparse
from colorama import Fore, Style, init
from collections import Counter

# Initialize colorama
init(autoreset=True)

class SchemaAnalyzer:
    """Analyzes a CSV file to infer the schema (data types) of its columns."""
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.header = []
        self.schema = []
        self.email_regex = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")

    def analyze(self, analysis_rows=50):
        """Reads the CSV and infers the schema."""
        print(f"Analyzing schema from '{self.csv_path.name}'...")
        with open(self.csv_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f)
            self.header = next(reader)
            
            # Transpose rows to get columns
            columns = [[] for _ in self.header]
            for i, row in enumerate(reader):
                if i >= analysis_rows:
                    break
                for j, cell in enumerate(row):
                    if j < len(columns):
                        columns[j].append(cell)
        
        for i, col_data in enumerate(columns):
            self.schema.append({
                "name": self.header[i],
                "type": self._infer_type(col_data),
                "index": i
            })
        
        print("Schema analysis complete.")
        return self.schema, len(self.header)

    def _infer_type(self, column_data):
        """Infers the most likely type for a column based on its data."""
        types = []
        for item in column_data:
            if not item or item.lower() == 'null':
                continue
            if item.isdigit():
                types.append('integer')
            elif self.email_regex.match(item):
                types.append('email')
            else:
                types.append('string')
        
        if not types:
            return 'string' # Default if all are empty
        
        # Return the most common type found
        return Counter(types).most_common(1)[0][0]

class RowRepairer:
    """Attempts to repair a single row of data based on a target schema."""
    def __init__(self, schema):
        self.schema = schema
        self.email_regex = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")

    def repair(self, bad_row_values):
        """
        Tries to align the bad row to the schema using a sliding window approach
        and returns the best-aligned, padded row.
        """
        best_offset = 0
        highest_score = -1

        # Try every possible alignment (offset)
        for offset in range(-len(bad_row_values), len(self.schema)):
            current_score = 0
            for i, value in enumerate(bad_row_values):
                target_index = i + offset
                if 0 <= target_index < len(self.schema):
                    current_score += self._calculate_match_score(value, self.schema[target_index]['type'])
            
            if current_score > highest_score:
                highest_score = current_score
                best_offset = offset
        
        # If no good match was found, we can't repair it
        if highest_score <= 0:
            return None

        # Reconstruct the row with the best alignment
        repaired_row = ["NULL"] * len(self.schema)
        for i, value in enumerate(bad_row_values):
            target_index = i + best_offset
            if 0 <= target_index < len(self.schema):
                repaired_row[target_index] = value
        
        return repaired_row

    def _calculate_match_score(self, value, expected_type):
        """Calculates a confidence score for a value matching an expected type."""
        if not value or value.lower() == 'null':
            return 0
        
        if expected_type == 'email' and self.email_regex.match(value):
            return 10  # High score for a clear anchor
        if expected_type == 'integer' and value.isdigit():
            return 5   # Medium score for a good anchor
        if expected_type == 'string' and value:
            return 1   # Low score for any non-empty string
        return 0

class SqlRepair:
    def __init__(self, wrong_length_file):
        self.wrong_length_path = Path(wrong_length_file)
        if not self.wrong_length_path.is_file():
            raise FileNotFoundError(f"Input file not found: '{wrong_length_file}'")

        self.csv_path = self._derive_csv_path()
        if not self.csv_path.is_file():
            raise FileNotFoundError(f"Corresponding CSV not found: '{self.csv_path}'")
            
        self.failed_recovery_path = self.wrong_length_path.with_name(self.wrong_length_path.stem + '_failed_recovery.txt')
        self.values_regex = re.compile(r'VALUES\s*(.*)', re.IGNORECASE | re.DOTALL)

    def _derive_csv_path(self):
        base_name = self.wrong_length_path.name.replace('_wrong_length.txt', '.csv')
        return self.wrong_length_path.parent / base_name

    def _parse_values_string(self, values_str):
        # This function remains the same as the robust one from the main parser
        rows = []
        in_string, paren_level, char_buffer = False, 0, []
        values_str = values_str.strip().removesuffix(';')
        for char in values_str:
            if char == "'" and (not char_buffer or char_buffer[-1] != '\\'):
                in_string = not in_string
            if not in_string and char == '(':
                paren_level += 1
                if paren_level == 1: char_buffer = []; continue
            elif not in_string and char == ')':
                paren_level -= 1
                if paren_level == 0:
                    try:
                        rows.append(next(csv.reader(["".join(char_buffer).strip()], escapechar='\\')))
                    except Exception:
                        rows.append("".join(char_buffer).strip().split(','))
                    char_buffer = []; continue
            if paren_level > 0: char_buffer.append(char)
        return rows

    def run_recovery(self):
        analyzer = SchemaAnalyzer(self.csv_path)
        schema, expected_cols = analyzer.analyze()
        repairer = RowRepairer(schema)
        
        table_name = self.csv_path.name.split(' - ')[1].replace('.csv', '')
        print(f"Attempting to repair rows for table '{Style.BRIGHT}{table_name}{Style.RESET_ALL}'.")

        failed_lines = self.wrong_length_path.read_text(encoding='utf-8', errors='replace').splitlines()
        recovered_rows, still_failed = [], []

        for line in failed_lines:
            line = line.strip()
            if not line: continue

            values_match = self.values_regex.search(line)
            values_str = values_match.group(1) if values_match else line
            
            reparsed_rows = self._parse_values_string(values_str)
            for row_values in reparsed_rows:
                repaired_row = repairer.repair(row_values)
                if repaired_row:
                    recovered_rows.append(repaired_row + [table_name])
                else:
                    still_failed.append(str(row_values))
        
        if recovered_rows:
            with open(self.csv_path, 'a', encoding='utf-8', errors='replace', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(recovered_rows)
            print(f"{Fore.GREEN}Successfully recovered and appended {len(recovered_rows)} rows to {self.csv_path.name}.")

        if still_failed:
            self.failed_recovery_path.write_text("\n".join(still_failed), encoding='utf-8', errors='replace')
            print(f"{Fore.YELLOW}{len(still_failed)} rows could not be recovered. See {self.failed_recovery_path.name}.")
        
        if not recovered_rows and not still_failed:
            print(f"{Fore.BLUE}No rows were found to process in the file.")

def main():
    banner = f"""{Fore.CYAN}
     _____  ____  _   _ ____                
    |  ___|/ ___|| | | |  _ \ ___ _ __   ___ 
    | |_  | |   | |_| | |_) / _ \ '_ \ / _ \
    |  _| | |___|  _  |  _ <  __/ |_) |  __/
    |_|    \____|_| |_|_| \_\\___| .__/ \___|
                               |_|          

    {Style.BRIGHT}SQL Parser+ Row Recovery Tool{Style.RESET_ALL}
    """
    print(banner)
    parser = argparse.ArgumentParser(description="Intelligently repairs and appends rows from a '_wrong_length.txt' file to its corresponding CSV.")
    parser.add_argument('wrong_length_file', help="Path to the '_wrong_length.txt' file to process.")
    args = parser.parse_args()

    try:
        SqlRepair(args.wrong_length_file).run_recovery()
    except FileNotFoundError as e:
        print(f"{Fore.RED}{e}")
        sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()