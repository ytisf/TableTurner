# 🌀 TableTurner: Your SQL-to-CSV Sidekick

Tired of wrestling with massive SQL dump files? Feeling the pain of trying to manually extract data for analysis or migration? Meet **TableTurner**, the friendly neighborhood tool that turns your SQL tables into sparkling clean CSV files with a flick of the wrist\!

Whether you're a data wizard, a developer on a mission, or just someone who wants to make life a little easier, TableTurner is here to help you get the job done without breaking a sweat.

This project was inspired by the fantastic work of `citcheese` and their [SqlParserPlus](https://github.com/citcheese/SqlParserPlus) tool. Their original project served as a great foundation and a source of inspiration for the features and approach used in TableTurner. We extend our sincere gratitude for their contributions to the open-source community!

## 🚀 Features That'll Make You Smile

  * **SQL to CSV Conversion**: Effortlessly parse those bulky SQL `INSERT` statements and transform them into beautiful, usable CSV files.
  * **Dual Interfaces**: Choose your adventure\! Use the intuitive **GUI** (built with PyQt6) for a visual experience, or fire up the lightning-fast **TUI** (built with curses) for a keyboard-driven workflow.
  * **Selective Service**: Don't need everything? No problem\! Our interactive table selector lets you pick and choose exactly which tables you want to extract from your SQL dump.
  * **Rock-Solid Parsing**: We've built TableTurner to handle all sorts of SQL dump formats and massive file sizes like a pro.
  * **Row Repair**: Got some messy data? Our built-in row repair tool attempts to fix rows with incorrect column counts, saving you from a data-related headache.
  * **More Than Just SQL**: TableTurner is a versatile data-wrangling hero\! It can also extract email addresses from files and convert Excel files to CSV.

## 🔧 Getting Started (It's Easy\!)

### Requirements

First, you'll need to install a few Python packages. You can find them all in the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

*Don't worry, we've got all the essentials covered, from `PyQt6` for the GUI to `tqdm` for those sweet progress bars\!*

### Usage

**The GUI Version**
For a point-and-click good time, simply run:

```bash
python SqlParserPlusGUI.py
```

**The TUI Version**
For the command-line connoisseurs, use:

```bash
python SqlParserPlusTUI.py <path_to_sql_file>
```

Feeling impatient? Use the `--dumpall` flag to skip the interactive selector and extract all the tables in one go:

```bash
python SqlParserPlusTUI.py <path_to_sql_file> --dumpall
```

## 📜 License

This project is open-source and licensed under the MIT License. Feel free to peek under the hood and use it however you like\! See the `LICENSE.md` file for all the details.

## 🤝 Contributing

We love collaboration\! If you've got an idea, found a bug, or just want to make TableTurner even better, don't hesitate to open an issue or submit a pull request. Your contributions are what make this project awesome\!