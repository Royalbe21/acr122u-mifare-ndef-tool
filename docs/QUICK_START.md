# Quick Start

## 1. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

## 2. Set your config

For a generic setup:

```powershell
copy config.example.json config.json
```

For Master of Repairs:

```powershell
copy config.master-of-repairs.template.json config.json
```

## 3. Run

```powershell
python .\master_nfc_writer.py
```

For the Windows 11 desktop app:

```powershell
.\run_windows11_app.bat
```

## 4. Write one card

```text
1. Business Card Mode
1. Format + write default business card
```

## 5. Batch write cards

```text
1. Business Card Mode
4. Batch format + write default business card
```

## 6. Build the Windows 11 app

```powershell
.\scripts\build_windows11_app.ps1
```
