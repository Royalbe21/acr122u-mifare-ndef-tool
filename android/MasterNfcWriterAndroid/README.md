# Master NFC Writer Android

Android version of **Master NFC Writer**.

This app turns an Android phone with NFC into a basic NFC business-card writer.

## What it does

- Scans NFC cards
- Reads UID
- Reads/decodes NDEF URL/text records
- Writes URL, phone, email, and text records
- Tries Android `Ndef` writing first
- Tries Android `NdefFormatable` formatting when available
- Includes a MIFARE Classic 1K fallback formatter/writer for owned cards

## Important compatibility note

MIFARE Classic support is device-dependent on Android. Some Android phones expose `MifareClassic`; some do not. If the phone does not expose `MifareClassic` or `NdefFormatable`, the app may not be able to format/write MIFARE Classic cards.

For the most universal NFC business cards, NTAG213/215/216 cards are still the safer production choice.

## Open in Android Studio

1. Open Android Studio.
2. Choose **Open**.
3. Select this folder:

```text
android/MasterNfcWriterAndroid
```

4. Let Android Studio sync Gradle.
5. Plug in an Android phone with NFC.
6. Run the app on the phone.

## Use

1. Open the app.
2. Choose `Scan / Read Card` and tap a card.
3. For a blank card, choose `Format + Write`.
4. For a card already formatted once, choose `Write Only`.
5. Tap the card to the back of the phone.

## Safety

Use only on blank cards or cards you own.

Do not use this app on access badges, employee IDs, transit cards, hotel cards, apartment/gate cards, gym cards, or any card that controls access.
