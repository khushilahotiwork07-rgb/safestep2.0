import ast, sys, os

files = [
    'main.py',
    'database.py',
    'patients.py',
    'scoring.py',
    'vitals_simulator.py',
    'alerts.py',
    'time_predictor.py',
    'utils/helpers.py',
    'pages/ward_overview.py',
    'pages/patient_detail.py',
    'pages/active_alerts.py',
    'pages/alert_history.py',
    'pages/handover_summary.py',
]

errors = []
for f in files:
    try:
        src = open(f, encoding='utf-8').read()
        ast.parse(src)
        print(f'OK: {f}')
    except SyntaxError as e:
        errors.append(f'SYNTAX ERROR in {f}: {e}')
        print(errors[-1])
    except Exception as e:
        errors.append(f'ERROR in {f}: {e}')
        print(errors[-1])

if not errors:
    print('\nAll files parsed successfully - no syntax errors.')
else:
    print(f'\n{len(errors)} error(s) found.')
    sys.exit(1)
