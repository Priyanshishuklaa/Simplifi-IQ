# analyze_logs.py
# Reads a CSV of task logs and produces summary metrics and a single combined summary CSV.
import pandas as pd
import sys

def analyze(input_csv, output_summary_csv=None):
    # Read
    df = pd.read_csv(input_csv)
    df_original = df.copy()

    # Clean
    df['start'] = pd.to_datetime(df['start'], errors='coerce')
    df['duration_min'] = pd.to_numeric(df['duration_min'], errors='coerce')

    # Identify invalids
    invalid_timestamp = df['start'].isna()
    invalid_duration = df['duration_min'].isna()
    negative_duration = df['duration_min'] < 0
    invalid_mask = invalid_timestamp | invalid_duration | negative_duration

    invalid_rows = df[invalid_mask].copy()
    valid_df = df[~invalid_mask].copy()

    # Aggregations
    time_per_user = valid_df.groupby('user', as_index=False)['duration_min'].sum().rename(columns={'duration_min':'total_minutes'})
    time_per_task = valid_df.groupby('task_type', as_index=False)['duration_min'].sum().rename(columns={'duration_min':'total_minutes'})
    top3_tasks = time_per_task.sort_values('total_minutes', ascending=False).head(3).reset_index(drop=True)

    summary = {
        'time_per_user': time_per_user,
        'time_per_task': time_per_task,
        'top3_tasks': top3_tasks,
        'invalid_rows': invalid_rows
    }

    # Build a single combined CSV if requested
    if output_summary_csv:
        rows = []

        # Section header + rows for time_per_user
        rows.append({'section':'time_per_user','c1':'user','c2':'total_minutes','c3':'','c4':''})
        for _, r in time_per_user.iterrows():
            rows.append({'section':'time_per_user','c1':r['user'],'c2':r['total_minutes'],'c3':'','c4':''})

        # blank line separator
        rows.append({'section':'','c1':'','c2':'','c3':'','c4':''})

        # time_per_task
        rows.append({'section':'time_per_task','c1':'task_type','c2':'total_minutes','c3':'','c4':''})
        for _, r in time_per_task.iterrows():
            rows.append({'section':'time_per_task','c1':r['task_type'],'c2':r['total_minutes'],'c3':'','c4':''})

        rows.append({'section':'','c1':'','c2':'','c3':'','c4':''})

        # top3_tasks with ranks
        rows.append({'section':'top3_tasks','c1':'rank','c2':'task_type','c3':'total_minutes','c4':''})
        for i, r in top3_tasks.reset_index(drop=True).iterrows():
            rows.append({'section':'top3_tasks','c1':i+1,'c2':r['task_type'],'c3':r['total_minutes'],'c4':''})

        rows.append({'section':'','c1':'','c2':'','c3':'','c4':''})

        # invalid rows: show original columns + reason
        rows.append({'section':'invalid_rows','c1':'user','c2':'task_type','c3':'start','c4':'reason'})
        for _, r in invalid_rows.iterrows():
            reasons = []
            if pd.isna(r['start']): reasons.append('bad_timestamp')
            if pd.isna(r['duration_min']): reasons.append('missing_duration')
            if (not pd.isna(r['duration_min'])) and r['duration_min'] < 0: reasons.append('negative_duration')
            rows.append({'section':'invalid_rows','c1':r.get('user',''),'c2':r.get('task_type',''),'c3':r.get('start',''),'c4':','.join(reasons)})

        out_df = pd.DataFrame(rows, columns=['section','c1','c2','c3','c4'])
        out_df.to_csv(output_summary_csv, index=False)

    return summary

if __name__ == '__main__':
    input_csv = sys.argv[1] if len(sys.argv) > 1 else 'task_logs_sample.csv'
    out_csv = sys.argv[2] if len(sys.argv) > 2 else 'summary_report.csv'
    s = analyze(input_csv, out_csv)
    # Print short console output
    print('=== Time per user ===')
    print(s['time_per_user'].to_string(index=False))
    print('\n=== Time per task ===')
    print(s['time_per_task'].to_string(index=False))
    print('\n=== Top 3 task types ===')
    print(s['top3_tasks'].to_string(index=False))
    print('\nCombined summary written to:', out_csv)
