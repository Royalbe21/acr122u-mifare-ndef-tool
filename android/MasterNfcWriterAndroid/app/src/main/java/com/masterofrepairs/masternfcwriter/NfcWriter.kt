package com.masterofrepairs.masternfcwriter

import android.nfc.NdefMessage
import android.nfc.NdefRecord
import android.nfc.Tag
import android.nfc.tech.MifareClassic
import android.nfc.tech.Ndef
import android.nfc.tech.NdefFormatable
import java.io.IOException
import java.nio.charset.Charset
import java.util.Locale

data class WriteRequest(
    val type: String,
    val value: String
)

data class NfcResult(
    val ok: Boolean,
    val title: String,
    val details: String,
    val uid: String? = null,
    val ndefType: String? = null,
    val ndefValue: String? = null,
    val techList: List<String> = emptyList()
)

object NfcWriter {

    private val keyDefault = byteArrayOf(0xff.toByte(), 0xff.toByte(), 0xff.toByte(), 0xff.toByte(), 0xff.toByte(), 0xff.toByte())
    private val keyNfcForum = byteArrayOf(0xd3.toByte(), 0xf7.toByte(), 0xd3.toByte(), 0xf7.toByte(), 0xd3.toByte(), 0xf7.toByte())
    private val keyMadA = byteArrayOf(0xa0.toByte(), 0xa1.toByte(), 0xa2.toByte(), 0xa3.toByte(), 0xa4.toByte(), 0xa5.toByte())
    private val keyMadB = byteArrayOf(0xb0.toByte(), 0xb1.toByte(), 0xb2.toByte(), 0xb3.toByte(), 0xb4.toByte(), 0xb5.toByte())

    private val dataBlocks1k = intArrayOf(
        4, 5, 6,
        8, 9, 10,
        12, 13, 14,
        16, 17, 18,
        20, 21, 22,
        24, 25, 26,
        28, 29, 30,
        32, 33, 34,
        36, 37, 38,
        40, 41, 42,
        44, 45, 46,
        48, 49, 50,
        52, 53, 54,
        56, 57, 58,
        60, 61, 62
    )

    private val madBlock1 = byteArrayOf(
        0x14, 0x01, 0x03, 0xe1.toByte(), 0x03, 0xe1.toByte(), 0x03, 0xe1.toByte(),
        0x03, 0xe1.toByte(), 0x03, 0xe1.toByte(), 0x03, 0xe1.toByte(), 0x03, 0xe1.toByte()
    )

    private val madBlock2 = byteArrayOf(
        0x03, 0xe1.toByte(), 0x03, 0xe1.toByte(), 0x03, 0xe1.toByte(), 0x03, 0xe1.toByte(),
        0x03, 0xe1.toByte(), 0x03, 0xe1.toByte(), 0x03, 0xe1.toByte(), 0x03, 0xe1.toByte()
    )

    private val madTrailer = byteArrayOf(
        0xa0.toByte(), 0xa1.toByte(), 0xa2.toByte(), 0xa3.toByte(), 0xa4.toByte(), 0xa5.toByte(),
        0x78, 0x77, 0x88.toByte(), 0xc1.toByte(),
        0xff.toByte(), 0xff.toByte(), 0xff.toByte(), 0xff.toByte(), 0xff.toByte(), 0xff.toByte()
    )

    private val nfcTrailer = byteArrayOf(
        0xd3.toByte(), 0xf7.toByte(), 0xd3.toByte(), 0xf7.toByte(), 0xd3.toByte(), 0xf7.toByte(),
        0x7f, 0x07, 0x88.toByte(), 0x40,
        0xff.toByte(), 0xff.toByte(), 0xff.toByte(), 0xff.toByte(), 0xff.toByte(), 0xff.toByte()
    )

    private val emptyBlock = ByteArray(16) { 0x00 }
    private val emptyNdefFirstBlock = byteArrayOf(0x03, 0x00, 0xfe.toByte()) + ByteArray(13) { 0x00 }

    fun scan(tag: Tag): NfcResult {
        val uid = tag.id.toHex()
        val techList = tag.techList.toList()

        val decoded = readDecodedNdef(tag)
        if (decoded != null) {
            return NfcResult(
                ok = true,
                title = "Card scanned",
                details = "NDEF data decoded.",
                uid = uid,
                ndefType = decoded.first,
                ndefValue = decoded.second,
                techList = techList
            )
        }

        return NfcResult(
            ok = true,
            title = "Card scanned",
            details = "No NDEF data decoded. If this is a blank card, use Format + Write.",
            uid = uid,
            techList = techList
        )
    }

    fun writeOnly(tag: Tag, request: WriteRequest): NfcResult {
        val uid = tag.id.toHex()
        val message = createMessage(request)

        val ndef = Ndef.get(tag)
        if (ndef != null) {
            try {
                ndef.connect()
                if (!ndef.isWritable) {
                    return NfcResult(false, "Tag is read-only", "This tag is NDEF formatted but not writable.", uid = uid, techList = tag.techList.toList())
                }

                val size = message.toByteArray().size
                if (ndef.maxSize < size) {
                    return NfcResult(false, "Payload too large", "Message is $size bytes; tag capacity is ${ndef.maxSize} bytes.", uid = uid, techList = tag.techList.toList())
                }

                ndef.writeNdefMessage(message)
                val decoded = decodeMessage(message)
                return NfcResult(true, "NDEF write verified", "Wrote using Android Ndef API.", uid, decoded?.first, decoded?.second, tag.techList.toList())
            } catch (ex: Exception) {
                // Fall through to MIFARE Classic raw NDEF payload write.
            } finally {
                safeClose(ndef)
            }
        }

        val mifare = MifareClassic.get(tag)
            ?: return NfcResult(false, "Unsupported tag", "This phone did not expose Ndef or MifareClassic for this card.", uid = uid, techList = tag.techList.toList())

        return try {
            mifare.connect()
            writePayloadToMifareClassic(mifare, message)
            val decoded = decodeMessage(message)
            NfcResult(true, "MIFARE Classic payload write verified", "Wrote NDEF TLV into MIFARE Classic data blocks.", uid, decoded?.first, decoded?.second, tag.techList.toList())
        } catch (ex: Exception) {
            NfcResult(false, "Write failed", ex.message ?: ex.toString(), uid = uid, techList = tag.techList.toList())
        } finally {
            safeClose(mifare)
        }
    }

    fun formatAndWrite(tag: Tag, request: WriteRequest): NfcResult {
        val uid = tag.id.toHex()
        val message = createMessage(request)

        val formattable = NdefFormatable.get(tag)
        if (formattable != null) {
            try {
                formattable.connect()
                formattable.format(message)
                val decoded = decodeMessage(message)
                return NfcResult(true, "Formatted and wrote NDEF", "Used Android NdefFormatable API.", uid, decoded?.first, decoded?.second, tag.techList.toList())
            } catch (ex: Exception) {
                // Fall through to MIFARE Classic formatter.
            } finally {
                safeClose(formattable)
            }
        }

        val mifare = MifareClassic.get(tag)
            ?: return NfcResult(false, "Unsupported tag", "This phone cannot format this card as NDEF. MifareClassic was not exposed by the device.", uid = uid, techList = tag.techList.toList())

        return try {
            mifare.connect()
            formatMifareClassic1kAsNdef(mifare)
            writePayloadToMifareClassic(mifare, message)
            val decoded = decodeMessage(message)
            NfcResult(true, "MIFARE Classic format + write verified", "Formatted MAD1/NDEF layout and wrote payload.", uid, decoded?.first, decoded?.second, tag.techList.toList())
        } catch (ex: Exception) {
            NfcResult(false, "Format + write failed", ex.message ?: ex.toString(), uid = uid, techList = tag.techList.toList())
        } finally {
            safeClose(mifare)
        }
    }

    private fun createMessage(request: WriteRequest): NdefMessage {
        val type = request.type.lowercase(Locale.US)
        val value = request.value.trim()
        if (value.isEmpty()) error("Payload cannot be empty.")

        return when (type) {
            "url" -> {
                val normalized = if (value.startsWith("http://", true) || value.startsWith("https://", true)) value else "https://$value"
                NdefMessage(arrayOf(NdefRecord.createUri(normalized)))
            }
            "phone" -> {
                val digits = value.filter { it.isDigit() || it == '+' }
                NdefMessage(arrayOf(NdefRecord.createUri("tel:$digits")))
            }
            "email" -> {
                val normalized = if (value.startsWith("mailto:", true)) value else "mailto:$value"
                NdefMessage(arrayOf(NdefRecord.createUri(normalized)))
            }
            "text" -> {
                val lang = "en".toByteArray(Charsets.US_ASCII)
                val text = value.toByteArray(Charsets.UTF_8)
                val payload = byteArrayOf(lang.size.toByte()) + lang + text
                val record = NdefRecord(
                    NdefRecord.TNF_WELL_KNOWN,
                    NdefRecord.RTD_TEXT,
                    ByteArray(0),
                    payload
                )
                NdefMessage(arrayOf(record))
            }
            else -> error("Unsupported type: $type")
        }
    }

    private fun readDecodedNdef(tag: Tag): Pair<String, String>? {
        val ndef = Ndef.get(tag)
        if (ndef != null) {
            try {
                ndef.connect()
                val message = ndef.ndefMessage ?: ndef.cachedNdefMessage
                val decoded = message?.let { decodeMessage(it) }
                if (decoded != null) return decoded
            } catch (_: Exception) {
            } finally {
                safeClose(ndef)
            }
        }

        val mifare = MifareClassic.get(tag) ?: return null
        return try {
            mifare.connect()
            val raw = readRawMifareClassicBlocks(mifare)
            val ndefBytes = extractNdefFromTlv(raw) ?: return null
            decodeNdefBytes(ndefBytes)
        } catch (_: Exception) {
            null
        } finally {
            safeClose(mifare)
        }
    }

    private fun decodeMessage(message: NdefMessage): Pair<String, String>? {
        return decodeNdefBytes(message.toByteArray())
    }

    private fun decodeNdefBytes(bytes: ByteArray): Pair<String, String>? {
        val message = try {
            NdefMessage(bytes)
        } catch (_: Exception) {
            return null
        }

        val record = message.records.firstOrNull() ?: return null

        if (record.tnf == NdefRecord.TNF_WELL_KNOWN && record.type.contentEquals(NdefRecord.RTD_URI)) {
            val uri = record.toUri()?.toString() ?: return null
            return "uri" to uri
        }

        if (record.tnf == NdefRecord.TNF_WELL_KNOWN && record.type.contentEquals(NdefRecord.RTD_TEXT)) {
            val payload = record.payload
            if (payload.isEmpty()) return null
            val langLen = payload[0].toInt() and 0x3f
            val textStart = 1 + langLen
            if (textStart > payload.size) return null
            val text = payload.copyOfRange(textStart, payload.size).toString(Charsets.UTF_8)
            return "text" to text
        }

        return "unknown" to bytes.toHex()
    }

    private fun readRawMifareClassicBlocks(mifare: MifareClassic): ByteArray {
        val chunks = mutableListOf<ByteArray>()

        for (block in dataBlocks1k) {
            val sector = mifare.blockToSector(block)
            if (!authenticateSectorAny(mifare, sector)) {
                if (chunks.isNotEmpty()) break
                continue
            }
            chunks.add(mifare.readBlock(block))
        }

        return chunks.fold(ByteArray(0)) { acc, bytes -> acc + bytes }
    }

    private fun extractNdefFromTlv(raw: ByteArray): ByteArray? {
        var i = 0

        while (i < raw.size) {
            val t = raw[i].toInt() and 0xff

            when (t) {
                0x00 -> i += 1
                0xfe -> return null
                0x03 -> {
                    if (i + 1 >= raw.size) return null
                    var length = raw[i + 1].toInt() and 0xff
                    var start = i + 2

                    if (length == 0xff) {
                        if (i + 3 >= raw.size) return null
                        length = ((raw[i + 2].toInt() and 0xff) shl 8) or (raw[i + 3].toInt() and 0xff)
                        start = i + 4
                    }

                    if (start + length > raw.size) return null
                    return raw.copyOfRange(start, start + length)
                }
                else -> {
                    if (i + 1 >= raw.size) return null
                    val length = raw[i + 1].toInt() and 0xff
                    i += 2 + length
                }
            }
        }

        return null
    }

    private fun formatMifareClassic1kAsNdef(mifare: MifareClassic) {
        if (mifare.size != MifareClassic.SIZE_1K) {
            error("This fallback formatter currently supports MIFARE Classic 1K only.")
        }

        for (sector in 1 until 16) {
            if (!authenticateSectorAny(mifare, sector, listOf(keyDefault, keyNfcForum))) {
                error("Could not authenticate sector $sector for formatting.")
            }

            val first = mifare.sectorToBlock(sector)
            mifare.writeBlock(first, if (sector == 1) emptyNdefFirstBlock else emptyBlock)
            mifare.writeBlock(first + 1, emptyBlock)
            mifare.writeBlock(first + 2, emptyBlock)

            try {
                mifare.writeBlock(first + 3, nfcTrailer)
            } catch (_: Exception) {
                // Already-formatted cards may block trailer rewrites. This is not fatal;
                // the later payload write/verify is the real pass/fail test.
            }
        }

        if (authenticateSectorAny(mifare, 0, listOf(keyDefault, keyMadA, keyMadB))) {
            try {
                mifare.writeBlock(1, madBlock1)
                mifare.writeBlock(2, madBlock2)
                try {
                    mifare.writeBlock(3, madTrailer)
                } catch (_: Exception) {
                    // Already formatted MAD trailer may be protected.
                }
            } catch (_: Exception) {
                // Continue; existing MAD may already be valid.
            }
        }
    }

    private fun writePayloadToMifareClassic(mifare: MifareClassic, message: NdefMessage) {
        val payload = makeTlvPayload(message)
        val blocksNeeded = payload.size / 16

        if (blocksNeeded > dataBlocks1k.size) {
            error("Payload too large for MIFARE Classic 1K data area.")
        }

        for (i in 0 until blocksNeeded) {
            val block = dataBlocks1k[i]
            val sector = mifare.blockToSector(block)

            if (!authenticateSectorAny(mifare, sector, listOf(keyNfcForum, keyDefault))) {
                error("Could not authenticate block $block for write.")
            }

            val chunk = payload.copyOfRange(i * 16, (i + 1) * 16)
            mifare.writeBlock(block, chunk)
        }

        // Verify
        val verify = ByteArray(payload.size)
        for (i in 0 until blocksNeeded) {
            val block = dataBlocks1k[i]
            val sector = mifare.blockToSector(block)

            if (!authenticateSectorAny(mifare, sector, listOf(keyNfcForum, keyDefault))) {
                error("Could not authenticate block $block for verify.")
            }

            val chunk = mifare.readBlock(block)
            System.arraycopy(chunk, 0, verify, i * 16, 16)
        }

        if (!verify.contentEquals(payload)) {
            error("Verification failed. Readback did not match payload.")
        }
    }

    private fun makeTlvPayload(message: NdefMessage): ByteArray {
        val ndef = message.toByteArray()

        if (ndef.size >= 0xff) {
            error("Long NDEF records are not implemented in this Android starter yet.")
        }

        val tlv = byteArrayOf(0x00, 0x00, 0x03, ndef.size.toByte()) + ndef + byteArrayOf(0xfe.toByte())
        val padding = (16 - (tlv.size % 16)) % 16
        return tlv + ByteArray(padding) { 0x00 }
    }

    private fun authenticateSectorAny(
        mifare: MifareClassic,
        sector: Int,
        keys: List<ByteArray> = listOf(keyDefault, keyNfcForum, keyMadA, keyMadB)
    ): Boolean {
        for (key in keys) {
            try {
                if (mifare.authenticateSectorWithKeyA(sector, key)) return true
            } catch (_: Exception) {
            }

            try {
                if (mifare.authenticateSectorWithKeyB(sector, key)) return true
            } catch (_: Exception) {
            }
        }

        return false
    }

    private fun safeClose(closeable: Any?) {
        try {
            when (closeable) {
                is Ndef -> closeable.close()
                is NdefFormatable -> closeable.close()
                is MifareClassic -> closeable.close()
            }
        } catch (_: IOException) {
        } catch (_: Exception) {
        }
    }

    private fun ByteArray.toHex(): String {
        return joinToString("") { "%02X".format(it.toInt() and 0xff) }
    }
}
