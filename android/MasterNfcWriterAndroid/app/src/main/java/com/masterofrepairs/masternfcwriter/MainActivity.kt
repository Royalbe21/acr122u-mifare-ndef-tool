package com.masterofrepairs.masternfcwriter

import android.app.Activity
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.*
import java.util.concurrent.atomic.AtomicReference

class MainActivity : Activity(), NfcAdapter.ReaderCallback {

    private var nfcAdapter: NfcAdapter? = null

    private lateinit var statusText: TextView
    private lateinit var uidText: TextView
    private lateinit var ndefText: TextView
    private lateinit var techText: TextView
    private lateinit var payloadInput: EditText
    private lateinit var recordTypeSpinner: Spinner
    private lateinit var actionText: TextView

    private val pendingAction = AtomicReference(NfcAction.Scan)

    enum class NfcAction {
        Scan,
        WriteOnly,
        FormatWrite
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        nfcAdapter = NfcAdapter.getDefaultAdapter(this)
        buildUi()

        if (nfcAdapter == null) {
            statusText.text = "This Android device does not have NFC."
            setButtonsEnabled(false)
        } else if (nfcAdapter?.isEnabled != true) {
            statusText.text = "NFC exists, but it is disabled. Turn NFC on in Android Settings."
        } else {
            statusText.text = "Ready. Choose an action, then tap a card to the phone."
        }
    }

    override fun onResume() {
        super.onResume()
        enableReaderMode()
    }

    override fun onPause() {
        super.onPause()
        nfcAdapter?.disableReaderMode(this)
    }

    private fun enableReaderMode() {
        val adapter = nfcAdapter ?: return

        val flags =
            NfcAdapter.FLAG_READER_NFC_A or
            NfcAdapter.FLAG_READER_NFC_B or
            NfcAdapter.FLAG_READER_NFC_V or
            NfcAdapter.FLAG_READER_NO_PLATFORM_SOUNDS

        adapter.enableReaderMode(this, this, flags, null)
    }

    override fun onTagDiscovered(tag: Tag) {
        val action = pendingAction.get()

        val result = when (action) {
            NfcAction.Scan -> NfcWriter.scan(tag)
            NfcAction.WriteOnly -> {
                val request = currentWriteRequest()
                NfcWriter.writeOnly(tag, request)
            }
            NfcAction.FormatWrite -> {
                val request = currentWriteRequest()
                NfcWriter.formatAndWrite(tag, request)
            }
        }

        runOnUiThread {
            showResult(result)
            if (action != NfcAction.Scan) {
                // Return to scan mode after a write attempt.
                pendingAction.set(NfcAction.Scan)
                actionText.text = "Current action: Scan"
            }
        }
    }

    private fun currentWriteRequest(): WriteRequest {
        val type = recordTypeSpinner.selectedItem.toString().lowercase()
        val value = payloadInput.text.toString().trim()
        return WriteRequest(type = type, value = value)
    }

    private fun showResult(result: NfcResult) {
        uidText.text = result.uid ?: "Unknown"
        techText.text = result.techList.joinToString("\n")

        if (result.ndefValue != null) {
            ndefText.text = "${result.ndefType}: ${result.ndefValue}"
        } else {
            ndefText.text = "No decoded NDEF"
        }

        statusText.text = if (result.ok) {
            "SUCCESS: ${result.title}\n${result.details}"
        } else {
            "ERROR: ${result.title}\n${result.details}"
        }
    }

    private fun buildUi() {
        val root = ScrollView(this)
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 32, 32, 32)
        }

        root.addView(layout)
        setContentView(root)

        val title = TextView(this).apply {
            text = "Master NFC Writer"
            textSize = 26f
            gravity = Gravity.START
        }
        layout.addView(title)

        val subtitle = TextView(this).apply {
            text = "Android NFC business-card writer for owned MIFARE Classic / NDEF tags"
            textSize = 14f
            setPadding(0, 4, 0, 24)
        }
        layout.addView(subtitle)

        statusText = TextView(this).apply {
            text = "Starting..."
            textSize = 15f
            setPadding(16, 16, 16, 16)
            setBackgroundColor(0xFFEFEFEF.toInt())
        }
        layout.addView(statusText, LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)

        addSection(layout, "Card Status")

        uidText = addValueRow(layout, "UID", "No card scanned")
        ndefText = addValueRow(layout, "NDEF", "No card scanned")
        techText = addValueRow(layout, "Tech", "No card scanned")

        val scanButton = Button(this).apply {
            text = "Scan / Read Card"
            setOnClickListener {
                pendingAction.set(NfcAction.Scan)
                actionText.text = "Current action: Scan - tap a card now"
                statusText.text = "Tap a card to scan/read it."
            }
        }
        layout.addView(scanButton)

        addSection(layout, "Write Payload")

        recordTypeSpinner = Spinner(this).apply {
            adapter = ArrayAdapter(
                this@MainActivity,
                android.R.layout.simple_spinner_dropdown_item,
                listOf("url", "phone", "email", "text")
            )
        }
        layout.addView(recordTypeSpinner)

        payloadInput = EditText(this).apply {
            hint = "https://blinq.me/your-card-link"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            setText("https://blinq.me/cmnuxghx600810as66v5d49ys?utm_medium=accessory")
            setSingleLine(false)
            minLines = 2
            maxLines = 4
        }
        layout.addView(payloadInput, LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)

        val writeOnlyButton = Button(this).apply {
            text = "Write Only - already formatted card"
            setOnClickListener {
                pendingAction.set(NfcAction.WriteOnly)
                actionText.text = "Current action: Write Only - tap an already-formatted owned card"
                statusText.text = "Tap an already-formatted card to write the payload."
            }
        }
        layout.addView(writeOnlyButton)

        val formatWriteButton = Button(this).apply {
            text = "Format + Write - blank/fresh owned card"
            setOnClickListener {
                pendingAction.set(NfcAction.FormatWrite)
                actionText.text = "Current action: Format + Write - tap a blank/fresh owned card"
                statusText.text = "Tap a blank/fresh owned card. This may change sector trailers."
            }
        }
        layout.addView(formatWriteButton)

        actionText = TextView(this).apply {
            text = "Current action: Scan"
            textSize = 15f
            setPadding(0, 18, 0, 8)
        }
        layout.addView(actionText)

        addSection(layout, "Safety")
        val safety = TextView(this).apply {
            text =
                "Use only on blank cards or cards you own. Do not use on access badges, hotel cards, " +
                "employee IDs, apartment/gate cards, transit cards, gym cards, or any card that controls access."
            textSize = 14f
        }
        layout.addView(safety)
    }

    private fun addSection(layout: LinearLayout, text: String) {
        val view = TextView(this).apply {
            this.text = text
            textSize = 20f
            setPadding(0, 28, 0, 8)
        }
        layout.addView(view)
    }

    private fun addValueRow(layout: LinearLayout, label: String, value: String): TextView {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, 8, 0, 8)
        }

        val labelView = TextView(this).apply {
            text = "$label:"
            textSize = 13f
        }

        val valueView = TextView(this).apply {
            text = value
            textSize = 15f
        }

        row.addView(labelView)
        row.addView(valueView)
        layout.addView(row)

        return valueView
    }

    private fun setButtonsEnabled(enabled: Boolean) {
        val root = (findViewById<View>(android.R.id.content) as? ViewGroup)
        // Kept simple for starter version. NFC status text already explains the issue.
    }
}
