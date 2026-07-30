"""GSM-7 alphabet handling and SMS segment counting.

Why this matters commercially: a message made only of GSM-7 characters fits 160
characters per segment. A single character outside the alphabet forces the whole
message to UCS-2, which fits 70. The Ghana cedi sign is not in GSM-7, so writing
it in a template roughly doubles the cost of every message that uses it. Always
write "GHS 120.00".
"""

# The GSM 03.38 basic character set.
GSM7_BASIC = set(
	"@£$¥èéùìòÇ\nØø\rÅå"
	"Δ_ΦΓΛΩΠΨΣΘΞÆæßÉ"
	" !\"#¤%&'()*+,-./0123456789:;<=>?"
	"¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§"
	"¿abcdefghijklmnopqrstuvwxyzäöñüà"
)

# Characters reachable only via the escape sequence. Each costs two septets.
GSM7_EXTENDED = set("^{}\\[~]|€")

GSM7 = GSM7_BASIC | GSM7_EXTENDED

SINGLE_GSM7 = 160
MULTI_GSM7 = 153
SINGLE_UCS2 = 70
MULTI_UCS2 = 67


def non_gsm7_characters(text: str) -> list[str]:
	"""Return the distinct characters that would force this message to UCS-2."""
	seen: dict[str, None] = {}
	for ch in text or "":
		if ch not in GSM7:
			seen.setdefault(ch, None)
	return list(seen)


def is_gsm7(text: str) -> bool:
	return not non_gsm7_characters(text)


def count_segments(text: str) -> tuple[str, int]:
	"""Return the encoding and the number of billable segments.

	>>> count_segments("Prime Shito: Order PS-7K2M-9XQD received.")
	('GSM-7', 1)
	"""
	text = text or ""

	if is_gsm7(text):
		# Extended characters occupy two septets each.
		length = sum(2 if ch in GSM7_EXTENDED else 1 for ch in text)
		if length <= SINGLE_GSM7:
			return "GSM-7", 1 if length else 0
		return "GSM-7", -(-length // MULTI_GSM7)

	# UCS-2 counts UTF-16 code units, so characters outside the BMP cost two.
	length = sum(2 if ord(ch) > 0xFFFF else 1 for ch in text)
	if length <= SINGLE_UCS2:
		return "UCS-2", 1 if length else 0
	return "UCS-2", -(-length // MULTI_UCS2)
