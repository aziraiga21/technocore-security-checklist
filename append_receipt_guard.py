import argparse
import json
import sys
from pathlib import Path


class ReceiptError(ValueError):
    """A write response does not prove exact post-write readback."""


def validate_append_receipt(response: dict) -> dict:
    if not isinstance(response, dict):
        raise ReceiptError("response root must be an object")
    posted = response.get("posted")
    messages = response.get("messages")
    if not isinstance(posted, dict) or type(posted.get("seq")) is not int:
        raise ReceiptError("posted must be an object with an integer sequence")
    if not isinstance(messages, list) or any(not isinstance(message, dict) for message in messages):
        raise ReceiptError("messages must be an array of record objects")
    if not isinstance(response.get("room"), str) or not response["room"]:
        raise ReceiptError("room must be a non-empty string")
    if type(response.get("generation")) is not int:
        raise ReceiptError("generation must be an integer")
    if type(response.get("count")) is not int or response["count"] != len(messages):
        raise ReceiptError("count does not match the message array")

    sequences = [message.get("seq") for message in messages]
    if sequences.count(posted["seq"]) > 1:
        raise ReceiptError("posted sequence appears more than once in the post-write room view")
    if any(type(sequence) is not int or sequence < 1 for sequence in sequences):
        raise ReceiptError("every message sequence must be a positive integer")
    if sequences != sorted(set(sequences)):
        raise ReceiptError("message sequences must be unique and strictly ascending")
    expected_first = sequences[0] if sequences else None
    expected_last = sequences[-1] if sequences else 0
    if response.get("first_seq") != expected_first:
        raise ReceiptError("first_seq does not match the room view")
    if response.get("last_seq") != expected_last:
        raise ReceiptError("last_seq does not match the room view")

    same_sequence = [message for message in messages if message.get("seq") == posted["seq"]]
    if not same_sequence:
        raise ReceiptError("posted record is absent from the post-write room view")
    if len(same_sequence) > 1:
        raise ReceiptError("posted sequence appears more than once in the post-write room view")
    if same_sequence[0] != posted:
        raise ReceiptError("read-back record does not exactly match the posted record")
    return posted


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify exact readback in a captured Technocore write response."
    )
    parser.add_argument("response", nargs="?", default="-", help="JSON file, or - for stdin")
    arguments = parser.parse_args()

    try:
        raw = (
            sys.stdin.read()
            if arguments.response == "-"
            else Path(arguments.response).read_text(encoding="utf-8")
        )
        try:
            response = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ReceiptError("response must be valid JSON") from error
        posted = validate_append_receipt(response)
        result = {"ok": True, "posted_seq": posted["seq"], "room": response["room"]}
        exit_code = 0
    except (OSError, ReceiptError) as error:
        result = {"findings": [str(error)], "ok": False}
        exit_code = 1

    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
