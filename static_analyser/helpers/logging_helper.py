import logging

logger = logging.getLogger("jarvis")
handler = logging.StreamHandler()
truncator = logging.Formatter("%(levelname)s: %(message)s")
handler.setFormatter(truncator)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


# import logging


# class EllipsisFormatter(logging.Formatter):
#     def __init__(self, fmt=None, datefmt=None, max_length=50):
#         super().__init__(fmt, datefmt)
#         self.max_length = max_length

#     def format(self, record):
#         # Make a copy of the message or record to avoid mutating the original
#         original_msg = record.getMessage()
#         if len(original_msg) > self.max_length:
#             record.msg = original_msg[: self.max_length] + "..."
#             record.args = None  # Clear args since msg is already interpolated
#         return super().format(record)


# # Example usage:
# logger = logging.getLogger("example")
# handler = logging.StreamHandler()
# handler.setFormatter(
#     EllipsisFormatter(fmt="[%(levelname)s] %(message)s", max_length=60)
# )
# logger.addHandler(handler)
# logger.setLevel(logging.DEBUG)
