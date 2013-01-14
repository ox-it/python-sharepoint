class SharePointException(Exception):
    pass

class UpdateFailedError(SharePointException):
    def __init__(self, row, update_type, code, text):
        self.row, self.update_type = row, update_type
        self.code, self.text = code, text

    def __str__(self):
        return 'Update ({0}) to row {1} ("{2}") failed: {3}, {4}'.format(
            self.update_type,
            self.row.ID,
            self.row.Title,
            self.code,
            self.text)