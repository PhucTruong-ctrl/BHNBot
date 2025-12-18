class Relationship:
    def __init__(self, user_id_1, user_id_2, affinity=0, last_interaction=None):
        self.user_id_1 = user_id_1
        self.user_id_2 = user_id_2
        self.affinity = affinity
        self.last_interaction = last_interaction

    @classmethod
    def from_db(cls, row):
        return cls(row[0], row[1], row[2], row[3])

class SharedPet:
    def __init__(self, partnership_id, name, exp, level, last_fed):
        self.partnership_id = partnership_id
        self.name = name
        self.exp = exp
        self.level = level
        self.last_fed = last_fed

    @classmethod
    def from_db(cls, row):
        return cls(row[0], row[1], row[2], row[3], row[4])

    @property
    def next_level_xp(self):
        # Example: Level 1 needs 100, Level 2 needs 200...
        return self.level * 100
