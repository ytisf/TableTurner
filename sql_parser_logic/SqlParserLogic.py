import re
import csv
import sys
from pathlib import Path
from tqdm import tqdm
from colorama import Fore

class SqlParser:
    def __init__(self, filepath, encoding="utf-8", show_progress=True):
        self.filepath = filepath
        self.filename = Path(filepath).name
        self.basepath = Path(filepath).parent
        self.encoding = encoding
        self.index = {}
        self.show_progress = show_progress
        self._initialize_constants()

    def _initialize_constants(self):
        """Initializes regex patterns and constants."""
        self.typelist = ["email", "username", "alias", "ipaddress", "ip_address", "address", "ip"]
        self.create_table_regex = re.compile(r'CREATE TABLE [`\'\"]?(\w+)[`\'\"]?', re.IGNORECASE)
        self.insert_regex = re.compile(r'INSERT INTO [`\'\"]?(\w+)[`\'\"]?', re.IGNORECASE)
        self.inline_headers_regex = re.compile(r'INSERT INTO.*?\( (.*?) \) \s* VALUES', re.IGNORECASE | re.DOTALL)
        self.values_regex = re.compile(r'VALUES\s*(.*)', re.IGNORECASE | re.DOTALL)

    def build_index(self):
        """Builds an index by reading the file line-by-line to avoid performance bottlenecks."""
        print("Building file index...")
        statement_buffer = []
        
        # Determine the iterator based on whether to show progress
        file_iterator = open(self.filepath, 'r', encoding=self.encoding, errors='replace')
        if self.show_progress:
            iterator = tqdm(file_iterator, desc="Indexing file")
        else:
            print("Indexing file...")
            iterator = file_iterator

        for line in iterator:
            line = line.strip()
            if not line:
                continue
            
            statement_buffer.append(line)
            if line.endswith(';'):
                full_statement = "\n".join(statement_buffer)
                
                create_match = self.create_table_regex.search(full_statement)
                if create_match:
                    table_name = create_match.group(1)
                    self._ensure_table_in_index(table_name)
                    self.index[table_name]['create'] = full_statement
                else:
                    insert_match = self.insert_regex.search(full_statement)
                    if insert_match:
                        table_name = insert_match.group(1)
                        self._ensure_table_in_index(table_name)
                        self.index[table_name]['inserts'].append(full_statement)
                
                statement_buffer = []
        
        file_iterator.close()
        if self.show_progress:
            iterator.close()

        print(f"Index complete. Found {Fore.LIGHTBLUE_EX}{len(self.index)}{Fore.RESET} tables.")
        return list(self.index.keys())

    def _ensure_table_in_index(self, table_name):
        """Helper to initialize a table's entry in the index if it doesn't exist."""
        if table_name not in self.index:
            self.index[table_name] = {'create': '', 'inserts': []}

    def _get_headers_from_create_stmt(self, create_statement):
        """Parses a CREATE TABLE statement to extract column names."""
        headers = []
        match = re.search(r'\((.*)\)', create_statement, re.DOTALL)
        if not match: return []
        
        content = re.sub(r'\([^)]*\)', '', match.group(1))
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.lower().startswith(('primary', 'unique', 'key', 'constraint', ')')):
                col_match = re.findall(r'^[ `\'\"]?(\w+)[`\'\"]?', line)
                if col_match:
                    headers.append(col_match[0])
        return headers

    def _parse_values_string(self, values_str):
        """
        Statefully parses a SQL VALUES string like `('a', 'b'), ('c', 'd')`.
        This is more robust than regex splitting for complex data.
        """
        rows = []
        current_row = []
        in_string = False
        paren_level = 0
        char_buffer = []
        
        for char in values_str:
            if char == "'" and (len(char_buffer) == 0 or char_buffer[-1] != '\\'):
                in_string = not in_string
            
            if not in_string:
                if char == '(':
                    paren_level += 1
                    if paren_level == 1: # Start of a new row tuple
                        char_buffer = []
                        continue
                elif char == ')':
                    paren_level -= 1
                    if paren_level == 0: # End of a row tuple
                        # Use csv.reader for robust field splitting
                        try:
                            parsed_fields = next(csv.reader([("".join(char_buffer).strip())], escapechar='\\'))
                            rows.append(parsed_fields)
                        except Exception:
                            # Fallback if csv reader fails
                            rows.append("".join(char_buffer).strip().split(','))
                        char_buffer = []
                        continue
            
            if paren_level > 0:
                char_buffer.append(char)
        return rows

    def process_table(self, table_name, format="csv"):
        """Processes all data for a single table and returns the output path."""
        if table_name not in self.index:
            return None

        table_info = self.index[table_name]
        default_headers = self._get_headers_from_create_stmt(table_info['create']) if table_info['create'] else []
        
        all_values, wrong_length, errors = [], [], []

        for insert_stmt in tqdm(table_info['inserts'], desc=f"Parsing {Fore.LIGHTBLUE_EX}{table_name}{Fore.RESET}", leave=False):
            try:
                active_headers = default_headers
                inline_headers_match = self.inline_headers_regex.search(insert_stmt)
                if inline_headers_match:
                    header_str = inline_headers_match.group(1).replace('`', '').replace('"', '').replace("'", "")
                    active_headers = [h.strip() for h in header_str.split(',')]

                values_match = self.values_regex.search(insert_stmt)
                if not values_match:
                    continue
                
                rows = self._parse_values_string(values_match.group(1))

                if not active_headers and rows:
                    num_cols = len(rows[0])
                    active_headers = [f'column_{i+1}' for i in range(num_cols)]
                    print(f"    {Fore.YELLOW}Warning: No headers found for {table_name}. Generated dummy columns.{Fore.RESET}")

                for row in rows:
                    if len(row) == len(active_headers):
                        all_values.append(row)
                    else:
                        wrong_length.append(str(row))
            except Exception as e:
                errors.append(f"{e} in statement: {insert_stmt[:100]}...")

        unique_values = [list(item) for item in set(tuple(row) for row in all_values)]
        if format == "csv":
            return self._write_to_csv(table_name, default_headers or (['column_1'] if unique_values else []), unique_values, wrong_length, errors)
        return None

    def _write_to_csv(self, target_table, headers, values, wronglength, errors):
        """Writes extracted data to a CSV file and returns the conversion path."""
        filename_stem = self.filename.rsplit(".", 1)[0].strip()
        conversions_path = self.basepath / "SqlConversions" / filename_stem
        conversions_path.mkdir(parents=True, exist_ok=True)
        
        bpath = conversions_path
        if any(h for h in headers if any(t in h for t in self.typelist)):
            good_ones_path = bpath / "Good Ones"
            good_ones_path.mkdir(exist_ok=True)
            bpath = good_ones_path

        if values:
            print(f"    Generating CSV for {target_table}")
            csv_path = bpath / f"{filename_stem} - {target_table}.csv"
            with open(csv_path, "w", encoding=self.encoding, newline='', errors="replace") as f:
                writer = csv.writer(f)
                csv_headers = headers + ["table"] if "table" not in headers else headers
                writer.writerow(csv_headers)
                for row in values:
                    if len(row) == len(headers):
                        writer.writerow(row + [target_table])
        else:
            print(f"    {Fore.RED}Found no values in {target_table}{Fore.RESET}")

        if wronglength:
            wrong_len_path = bpath / f"{filename_stem} - {target_table}_wrong_length.txt"
            wrong_len_path.write_text("\n".join(wronglength), encoding=self.encoding, errors="replace")
            print(f"    {Fore.YELLOW}{len(wronglength)} rows for {target_table} had incorrect column counts. See {wrong_len_path.name}{Fore.RESET}")

        if errors:
            errored_lines_path = bpath / f"{filename_stem}_ErroredLines.txt"
            with open(errored_lines_path, 'a', encoding=self.encoding, errors="replace") as outfile:
                outfile.write("\n".join(errors) + "\n")
        
        return conversions_path