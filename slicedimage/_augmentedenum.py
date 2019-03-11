from enum import Enum


class AugmentedEnum(Enum):
    def __hash__(self):
        return self.value.__hash__()

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.value == other.value
        return self.value == str(other)

    def __str__(self):
        return self.value
