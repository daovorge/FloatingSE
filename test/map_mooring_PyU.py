import numpy as np
import numpy.testing as npt
import unittest
import floatingse.map_mooring as mapMooring
from floatingse.column import ColumnGeometry
from pymap import pyMAP
from commonse import gravity as g

def myisnumber(instr):
    try:
        float(instr)
    except:
        return False
    return True

myones = np.ones((100,))
truth=['---------------------- LINE DICTIONARY ---------------------------------------',
'LineType  Diam      MassDenInAir   EA            CB   CIntDamp  Ca   Cdn    Cdt',
'(-)       (m)       (kg/m)        (N)           (-)   (Pa-s)    (-)  (-)    (-)',
'chain   0.05   53.77517   213500000.0   0.65   1.0E8   0.6   -1.0   0.05',
'---------------------- NODE PROPERTIES ---------------------------------------',
'Node Type X     Y    Z   M     V FX FY FZ',
'(-)  (-) (m)   (m)  (m) (kg) (m^3) (kN) (kN) (kN)',
'1   FIX   175.0   0.0   depth   0.0   0.0   #   #   #',
'2   VESSEL   11.0   0.0   -10.0   0.0   0.0   #   #   #',
'---------------------- LINE PROPERTIES ---------------------------------------',
'Line    LineType  UnstrLen  NodeAnch  NodeFair  Flags',
'(-)      (-)       (m)       (-)       (-)       (-)',
'1   chain   416.0   1   2',
'---------------------- SOLVER OPTIONS-----------------------------------------',
'Option',
'(-)',
'help',
' integration_dt 0',
' kb_default 3.0e6',
' cb_default 3.0e5',
' wave_kinematics',
'inner_ftol 1e-5',
'inner_gtol 1e-5',
'inner_xtol 1e-5',
'outer_tol 1e-3',
' pg_cooked 10000 1',
' outer_fd',
' outer_bd',
' outer_cd',
' inner_max_its 200',
' outer_max_its 600',
'repeat 120 240',
' krylov_accelerator 3',
' ref_position 0.0 0.0 0.0']


class TestMapMooring(unittest.TestCase):
    
    def setUp(self):
        self.params = {}
        self.unknowns = {}
        self.resid = None

        self.params['wall_thickness'] = np.array([0.5, 0.5, 0.5])
        self.params['outer_diameter'] = 2*np.array([10.0, 10.0, 10.0])
        self.params['section_height'] = np.array([20.0, 30.0])
        self.params['z_param_in'] = self.params['z_full_in'] = np.r_[0.0, np.cumsum(self.params['section_height'])]
        self.params['section_center_of_mass'] = np.array([10.0, 35.0])
        self.params['freeboard'] = 15.0
        self.params['fairlead'] = 10.0
        self.params['fairlead_radius'] = 11.0

        self.params['water_density'] = 1025.0 #1e3
        self.params['water_depth'] = 218.0 #100.0

        self.params['scope_ratio'] = 2.0
        self.params['mooring_diameter'] = 0.05
        self.params['anchor_radius'] = 175.0
        self.params['number_of_mooring_lines'] = 3
        self.params['mooring_type'] = 'chain'
        self.params['anchor_type'] = 'suctionpile'
        self.params['drag_embedment_extra_length'] = 300.0
        self.params['max_offset'] = 10.0
        self.params['max_heel'] = 10.0
        self.params['gamma'] = 1.35

        self.params['mooring_cost_rate'] = 1.1

        self.params['tower_base_radius'] = 4.0

        # Initialize an unknown
        self.unknowns['plot_matrix'] = np.zeros((15,20,3))
        
        self.set_geometry()

        self.mymap = mapMooring.MapMooring()
        self.mymap.set_properties(self.params)
        self.mymap.set_geometry(self.params, self.unknowns)
        #self.mymap.finput = open(mapMooring.FINPUTSTR, 'wb')
        
    #def tearDown(self):
        #self.mymap.finput.close()
        
    def set_geometry(self):
        geom = ColumnGeometry(2, 3)
        tempUnknowns = {}
        geom.solve_nonlinear(self.params, tempUnknowns, None)
        for pairs in tempUnknowns.items():
            self.params[pairs[0]] = pairs[1]

    def testSetProperties(self):
        pass
    '''
    def testWriteLineDict(self):
        self.mymap.write_line_dictionary(self.params)
        self.mymap.finput.close()
        A = self.read_input()

    def testWriteNode(self):
        self.mymap.write_node_properties_header()
        self.mymap.write_node_properties(1, 'fix',0,0,0)
        self.mymap.write_node_properties(2, 'vessel',0,0,0)
        self.mymap.finput.close()
        A = self.read_input()

    def testWriteLine(self):
        self.mymap.write_line_properties(self.params)
        self.mymap.finput.close()
        A = self.read_input()

    def testWriteSolver(self):
        self.mymap.write_solver_options(self.params)
        self.mymap.finput.close()
        A = self.read_input()
    '''
    def testWriteInputAll(self):
        self.mymap.write_input_file(self.params)
        actual = self.mymap.finput[:]
        expect = truth[:]
        self.assertEqual(len(expect), len(actual))
        
        for n in xrange(len(actual)):
            actualTok = actual[n].split()
            expectTok = expect[n].split()
            self.assertEqual(len(expectTok), len(actualTok))
            
            for k in xrange(len(actualTok)):
                if myisnumber(actualTok[k]):
                    self.assertEqual( float(actualTok[k]), float(expectTok[k]) )
                else:
                    self.assertEqual( actualTok[k], expectTok[k] )
            
    def testRunMap(self):
        self.mymap.runMAP(self.params, self.unknowns)

    def testCost(self):
        self.mymap.compute_cost(self.params, self.unknowns)
    
    def testListEntry(self):
        # Initiate MAP++ for this design
        mymap = pyMAP( )
        #mymap.ierr = 0
        mymap.map_set_sea_depth(self.params['water_depth'])
        mymap.map_set_gravity(g)
        mymap.map_set_sea_density(self.params['water_density'])
        mymap.read_list_input(truth)
        mymap.init( )
        mymap.displace_vessel(0, 0, 0, 0, 10, 0)
        mymap.update_states(0.0, 0)
        mymap.end()
        
        
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestMapMooring))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())
