from bot.services.positions import PositionService, PositionStateUnknown
class C:
 def __init__(self,rows):self.rows=rows
 def positions(self):return self.rows
def test_multiple_positions_are_unknown():
 try: PositionService(C([{'positionAmt':'1'},{'positionAmt':'-1'}])).current_position()
 except PositionStateUnknown: return
 assert False
def test_one_position_is_known():assert PositionService(C([{'symbol':'X','positionAmt':'1','entryPrice':'2'}])).current_position().symbol=='X'
