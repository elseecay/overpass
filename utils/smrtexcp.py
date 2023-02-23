class SmartException(Exception):

    def __init__(self, *message: str, original_exception: Exception = None):
        message = "\n".join(message)
        if original_exception:
            original_message = str(original_exception).rstrip(" \n\r\t")
            if len(message) > 0:
                message = f"{original_message}\n{'*' * 12}\n{message}"
            else:
                message = original_message
        super().__init__(message)
        self.original_exception = original_exception
