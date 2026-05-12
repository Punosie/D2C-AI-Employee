import gspread
from src.config import settings

SERVICE_ACCOUNT_KEY_PATH = settings.GOOGLE_SERVICE_ACCOUNT_JSON

gc = gspread.service_account(filename=SERVICE_ACCOUNT_KEY_PATH)

SPREADSHEET_ID = "1JdQHfPFpT9rLXCJ6PDep_WngOCk5fw-aKoO8xd6psMQ"


def print_first_row_from_all_sheets():
    try:
        sh = gc.open_by_key(SPREADSHEET_ID)

        print(f"Spreadsheet: {sh.title}")
        print(f"Total sheets: {len(sh.worksheets())}")

        for worksheet in sh.worksheets():
            print(f"\nSheet: {worksheet.title}")

            # Get first row
            first_row = worksheet.row_values(1)

            print("Row 1:", first_row)

    except gspread.exceptions.SpreadsheetNotFound:
        print("Spreadsheet not found or not shared with service account.")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print_first_row_from_all_sheets()
