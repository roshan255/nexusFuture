from bot.position_manager import PositionManager
class C:
 def __init__(self,rows):self.rows=rows
 def positions(self):return self.rows
def test_multiple_positions_is_unknown():assert PositionManager(C([{'positionAmt':'1'},{'positionAmt':'-1'}])).reconcile()==(None,False)
def test_one_position_is_known():assert PositionManager(C([{'symbol':'X','positionAmt':'1','entryPrice':'2'}])).reconcile()[1]
