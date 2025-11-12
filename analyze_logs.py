# analyze_logs.py
# Reads a CSV of task logs and produces summary metrics.
import pandas as pd
import sys

def analyze(input_csv, output_summary_csv=None):
    df = pd.read_csv(input_csv)

    # Keep original for reporting invalid rows
    df_original = df.copy()

    # Parse timestamps - invalid timestamps become NaT
    df['start'] = pd.to_datetime(df['start'], errors='coerce')

    # Convert duration to numeric - invalid -> NaN
    df['duration_min'] = pd.to_numeric(df['duration_min'], errors='coerce')

    # Identify invalid rows
    invalid_timestamp = df['start'].isna()
    invalid_duration = df['duration_min'].isna()
    negative_duration = df['duration_min'] < 0

    invalid_rows = df[ invalid_timestamp | invalid_duration | negative_duration ]

    # For analysis exclude invalid or negative durations
    valid_df = df[ ~(invalid_timestamp | invalid_duration | negative_duration) ].copy()

    # Aggregate total time per user
    time_per_user = valid_df.groupby('user', as_index=False)['duration_min'].sum().rename(columns={'duration_min':'total_minutes'})

    # Aggregate total time per task_type
    time_per_task = valid_df.groupby('task_type', as_index=False)['duration_min'].sum().rename(columns={'duration_min':'total_minutes'})

    # Top 3 task types by total time
    top3_tasks = time_per_task.sort_values('total_minutes', ascending=False).head(3).reset_index(drop=True)

    # Prepare summary dictionary / dataframe for output
    summary = {
        'time_per_user': time_per_user,
        'time_per_task': time_per_task,
        'top3_tasks': top3_tasks,
        'invalid_rows': invalid_rows
    }

    # Optionally save a combined CSV summary
    if output_summary_csv:
        # Save three tables into separate CSVs with suffixes
        time_per_user.to_csv(output_summary_csv.replace('.csv','_time_per_user.csv'), index=False)
        time_per_task.to_csv(output_summary_csv.replace('.csv','_time_per_task.csv'), index=False)
        top3_tasks.to_csv(output_summary_csv.replace('.csv','_top3_tasks.csv'), index=False)
        invalid_rows.to_csv(output_summary_csv.replace('.csv','_invalid_rows.csv'), index=False)

    return summary

if __name__ == '__main__':
    input_csv = sys.argv[1] if len(sys.argv)>1 else 'task_logs_sample.csv'
    out_csv = sys.argv[2] if len(sys.argv)>2 else None
    s = analyze(input_csv, out_csv)
    print('=== Time per user ===')
    print(s['time_per_user'].to_string(index=False))
    print('\n=== Time per task ===')
    print(s['time_per_task'].to_string(index=False))
    print('\n=== Top 3 task types ===')
    print(s['top3_tasks'].to_string(index=False))
    print('\n=== Invalid / excluded rows ===')
    if s['invalid_rows'].empty:
        print('None')
    else:
        print(s['invalid_rows'].to_string(index=False))
