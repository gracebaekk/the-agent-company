import pandas as pd

# Read the CSV file
df = pd.read_csv('attendance-2024-03-01.csv')

# Strip whitespace from column names and values
df.columns = df.columns.str.strip()
df = df.apply(lambda x: x.str.strip() if x.dtype == 'object' else x)

# Function to convert time to total minutes
def time_to_minutes(time_str):
    hour, minute = map(int, time_str.split(':'))
    return hour * 60 + minute

# Define the perfect attendance criteria
def is_perfect_attendance(clock_out):
    clock_out_minutes = time_to_minutes(clock_out)
    return 17 * 60 + 30 <= clock_out_minutes <= 18 * 60

# Filter employees with perfect attendance
perfect_attendance = df[df['Clock-out'].apply(is_perfect_attendance)]

# Create a new DataFrame for the report
report_df = perfect_attendance[['Name']]

# Save the report to an Excel file
report_df.to_excel('/tmp/workspace/2024-03-attendance-summary.xlsx', index=False)