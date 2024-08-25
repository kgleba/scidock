import questionary
from questionary.prompts.common import Choice, InquirerControl

__all__ = ('patch_inquirer_control',)


class ExtensibleInquirerControl(InquirerControl):
    WINDOW_SIZE = 20

    def __init__(self, choices, *args, **kwargs):
        super().__init__(choices, *args, **kwargs)

        self._choice_source = choices
        self._choice_index = 0

    def select_previous(self) -> None:
        if self._choice_index == 0:
            return

        if self.pointed_at == 0:
            new_window = self._choice_source[
                self._choice_index - self.WINDOW_SIZE : self._choice_index
            ]
            self.choices = [Choice.build(c) for c in new_window]

        self.pointed_at = (self.pointed_at - 1) % self.choice_count
        self._choice_index -= 1

    def select_next(self) -> None:
        if self._choice_index == len(self._choice_source) - 1:
            return

        if self.pointed_at == self.choice_count - 1:
            new_window = self._choice_source[
                self._choice_index + 1 : self._choice_index + self.WINDOW_SIZE + 1
            ]
            self.choices = [Choice.build(c) for c in new_window]

        self.pointed_at = (self.pointed_at + 1) % self.choice_count
        self._choice_index += 1


def patch_inquirer_control() -> None:
    questionary.prompts.select.InquirerControl = ExtensibleInquirerControl
