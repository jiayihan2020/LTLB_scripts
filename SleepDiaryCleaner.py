import pandas as pd
import re
import os
import platform
from subprocess import run
import numpy as np

# --- User Input ----

working_directory = "./"
sleep_diary_csv_raw = "SIT Diary_March 23, 2022_23.40.csv"

exported_WT_csv = "./WT2.csv"
exported_BT_csv = "./BT2.csv"
R_interpreter_location_windows = (
    "c:/Program Files/R/R-4.1.3/bin/Rscript.exe"  # Edit the filepath if required.
)
R_interpreter_location_UNIX = "/usr/bin/R"  # Edit the filepath if required.

# --------------------


def opening_sleep_diary(sleep_diary_location):
    df = pd.read_csv(sleep_diary_location, index_col=False, skiprows=1)
    df.drop(index=0, inplace=True)
    df.columns = df.columns.str.replace("\n", "")
    df.columns = df.columns.str.replace(r"Qualtrics\.Survey.*", "", regex=True)
    df.columns = df.columns.str.strip()
    df = df.rename(columns={"Subject Code (e.g. SITXXX)": "Subject"})
    df["Subject"] = df["Subject"].str.upper()
    pd.set_option("display.max_columns", None)

    return df


def detect_spurious_datetime(sleep_diary_location):
    """Attempts to detect any potential inaccurate bedtime and wake time durations and flag those errors in a separate txt document"""

    spurious_data = {}
    df = opening_sleep_diary(sleep_diary_location)
    df = df[
        [
            "Subject",
            "1. Date at bedtime",
            "2. Bedtime(24 hour format, e.g. 16:35) - HH:MM",
            "4. Date at wake-time",
            "5. Final wake time (24 hour format, e.g. 16:35) - HH:MM",
        ]
    ]
    df.sort_values(by=["Subject"], inplace=True)

    df["Bed Time"] = (
        df["1. Date at bedtime"]
        + " "
        + df["2. Bedtime(24 hour format, e.g. 16:35) - HH:MM"]
    )
    df["Wake Time"] = (
        df["4. Date at wake-time"]
        + " "
        + df["5. Final wake time (24 hour format, e.g. 16:35) - HH:MM"]
    )

    df = df.drop(df.columns[1:5], axis=1)

    df["Bed Time"] = pd.to_datetime(df["Bed Time"], format="%d/%m/%Y %H:%M")
    df["Wake Time"] = pd.to_datetime(df["Wake Time"], format="%d/%m/%Y %H:%M")

    for (
        index,
        row,
    ) in df.iterrows():

        if (
            round(
                pd.Timedelta(row["Wake Time"] - row["Bed Time"])
                / np.timedelta64(1, "h"),
                2,
            )
            < 0
        ) or (
            round(
                pd.Timedelta(row["Wake Time"] - row["Bed Time"])
                / np.timedelta64(1, "h"),
                2,
            )
            > 12
        ):
            if row["Subject"] not in spurious_data:
                spurious_data[row["Subject"]] = [(row["Bed Time"], row["Wake Time"])]
            else:
                spurious_data[row["Subject"]] += [(row["Bed Time"], row["Wake Time"])]
    if len(spurious_data) > 0:
        with open("sussy datetime.txt", "w") as text_file:
            for k in spurious_data.keys():
                text_file.write(f"{k}: {spurious_data[k]}\n")

    return spurious_data


def obtaining_WT(sleep_diary_location):
    df = opening_sleep_diary(sleep_diary_location)
    search_pattern = re.compile(r"Subject|^2\.|^4\.|5\.")
    df = df.filter(regex=search_pattern)

    df.rename(
        columns={
            "4. Date at wake-time": "WTSelectedDate",
            "2. Bedtime(24 hour format, e.g. 16:35) - HH:MM": "Bedtime",
            "5. Final wake time (24 hour format, e.g. 16:35) - HH:MM": "WakeTime",
        },
        inplace=True,
    )
    df = df[["Subject", "WTSelectedDate", "Bedtime", "WakeTime"]]
    df["WTSelectedDate"] = pd.to_datetime(df["WTSelectedDate"], format="%d/%m/%Y")
    if platform.system() == "Windows":
        df["WTSelectedDate"] = pd.to_datetime(df["WTSelectedDate"]).dt.strftime(
            "%#d/%#m/%Y"
        )
    else:

        df["WTSelectedDate"] = pd.to_datetime(df["WTSelectedDate"]).dt.strftime(
            "%-d/%-m/%Y"
        )
    if platform.system() == "Windows":
        df["Bedtime"] = pd.to_datetime(df["Bedtime"], format="%H:%M")
        df["Bedtime"] = pd.to_datetime(df["Bedtime"]).dt.strftime("%#I:%M %p")
        df[["Bedtime", "BedtimeAMPM"]] = df["Bedtime"].str.split(" ", 1, expand=True)
        df["WakeTime"] = pd.to_datetime(df["WakeTime"], format="%H:%M")
        df["WakeTime"] = pd.to_datetime(df["WakeTime"]).dt.strftime("%#I:%M %p")
        df[["WakeTime", "WakeTimeAMPM"]] = df["WakeTime"].str.split(" ", 1, expand=True)
        df = df[
            [
                "Subject",
                "WTSelectedDate",
                "Bedtime",
                "BedtimeAMPM",
                "WakeTime",
                "WakeTimeAMPM",
            ]
        ]
    else:
        df["Bedtime"] = pd.to_datetime(df["Bedtime"], format="%H:%M")
        df["Bedtime"] = pd.to_datetime(df["Bedtime"]).dt.strftime("%-I:%M %p")
        df[["Bedtime", "BedtimeAMPM"]] = df["Bedtime"].str.split(" ", 1, expand=True)
        df["WakeTime"] = pd.to_datetime(df["WakeTime"], format="%H:%M")
        df["WakeTime"] = pd.to_datetime(df["WakeTime"]).dt.strftime("%-I:%M %p")
        df[["WakeTime", "WakeTimeAMPM"]] = df["WakeTime"].str.split(" ", 1, expand=True)
        df = df[
            [
                "Subject",
                "WTSelectedDate",
                "Bedtime",
                "BedtimeAMPM",
                "WakeTime",
                "WakeTimeAMPM",
            ]
        ]
    df.sort_values(by=["Subject", "WTSelectedDate"], inplace=True)
    df.loc[df["Subject"].duplicated(), "Subject"] = ""
    df.to_csv("./WT4.csv", index=False, encoding="utf-8")

    return None


def obtaining_BT(sleep_diary_location):
    df = opening_sleep_diary(sleep_diary_location)
    search_pattern = re.compile(r"Subject|^1\.|^7\w.")
    df = df.filter(regex=search_pattern)
    df.rename(
        columns={
            df.columns[1]: "BTSelectedDate",
            df.columns[2]: "Naps",
            df.columns[3]: "StartNap1",
            df.columns[4]: "EndNap1",
            df.columns[5]: "StartNap2",
            df.columns[6]: "EndNap2",
            df.columns[7]: "StartNap3",
            df.columns[8]: "EndNap3",
            df.columns[9]: "StartNap4",
            df.columns[10]: "EndNap4",
            df.columns[11]: "StartNap5",
            df.columns[12]: "EndNap5",
        },
        inplace=True,
    )
    df["BTSelectedDate"] = pd.to_datetime(df["BTSelectedDate"], format="%d/%m/%Y")
    if platform.system() == "Windows":
        df["BTSelectedDate"] = pd.to_datetime(df["BTSelectedDate"]).dt.strftime(
            "%#d/%#m/%Y"
        )
    else:
        df["BTSelectedDate"] = pd.to_datetime(df["BTSelectedDate"]).dt.strftime(
            "%-d/%-m/%Y"
        )
    df.sort_values(by=["Subject", "BTSelectedDate"], inplace=True)
    for col in df.columns:
        if "StartNap" in col or "EndNap" in col:
            df[col] = pd.to_datetime(df[col], format="%H:%M")
            if platform.system() == "Windows":
                df[col] = pd.to_datetime(df[col]).dt.strftime("%#I:%M %p")
            else:
                df[col] = pd.to_datetime(df[col]).dt.strftime("%-I:%M %p")
    df.loc[df["Subject"].duplicated(), "Subject"] = ""

    df.to_csv("./BT2.csv", index=False, encoding="utf-8")

    return df


def exporting_to_csv_using_R(WT_CSV, BT_CSV):
    """Attempt to export the cruse csv file from preceding step to the version that can be parsed by SleepAnnotate R script."""
    crude_csv = [WT_CSV, BT_CSV]
    if not (os.path.isfile(WT_CSV) or os.path.isfile(BT_CSV)):
        print(
            "ERROR: Missing either the WT csv or the BT csv files.Please generate those files before proceeding!"
        )
        quit()

    if platform.system() == "Windows":
        for csv_file in crude_csv:
            filename_only = csv_file.split("/")[-1]
            try:
                print(f"Exporting {filename_only}....")
                run(
                    [f"{R_interpreter_location_windows}", "--vanilla", f"{csv_file}"],
                    shell=True,
                )
            except FileNotFoundError:
                print(
                    "ERROR: RScript.exe not found. Please ensure that R is installed. Make sure that the filepath for RScript.exe is also correct."
                )
                break
            else:
                print("Done!")
    elif platform.system() == "Linux" or platform.system() == "Darwin":
        for csv_file in crude_csv:
            filename_only = csv_file.split("/")[-1]
            try:
                print(f"Exporting {filename_only}....")
                run(
                    [f"{R_interpreter_location_UNIX}", "--vanilla", f"{csv_file}"],
                    shell=True,
                )
            except FileNotFoundError:
                print(
                    "ERROR: RScript.exe not found. Please ensure that R is installed. Make sure that the filepath for RScript.exe is also correct."
                )
                break
            else:
                print("Done!")
    else:
        print(
            "Unknown OS detected. The script currently only supports Windows, macOS, and Linux."
        )
    return


detect_spurious_datetime(sleep_diary_csv_raw)

# obtaining_BT(sleep_diary_csv_raw)
# obtaining_WT(sleep_diary_csv_raw)
