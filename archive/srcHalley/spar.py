from openmdao.main.api import Component, Assembly,convert_units
from openmdao.lib.datatypes.api import Float, Array, Str, Int, Bool
from openmdao.lib.drivers.api import SLSQPdriver
from numpy import array, cos, sinh, sin, cosh, log, exp, dot
from scipy.optimize import fmin, minimize
from sympy.solvers import solve
from sympy import Symbol
import math
from utils import full_stiffeners_table,thrust_table,plasticityRF,frustumVol,frustumCG,ID,waveProperties,waveU,waveUdot,CD,inertialForce,windPowerLaw,pipeBuoyancy,rootsearch,bisect,roots,calcPsi,dragForce,curWaveDrag,windDrag,calculateWindCurrentForces

class Spar(Component):
    """Environmental factor inputs."""
    gust_factor = Float(1.0, iotype='in', desc='gust factor')
    gravity = Float(9.806, iotype='in', units='m/s**2', desc='gravity')
    air_density = Float(1.198, iotype='in', units='kg/m**3', desc='density of air')
    water_density = Float(1025, iotype='in',units='kg/m**3',desc='density of water')
    water_depth = Float(iotype='in', units='m', desc='water depth')
    load_condition =  Str(iotype='in',desc='Load condition - N for normal or E for extreme')
    significant_wave_height = Float(iotype='in', units='m', desc='significant wave height')
    significant_wave_period = Float(iotype='in', units='m', desc='significant wave period')
    wind_reference_speed = Float(iotype='in', units='m/s', desc='reference wind speed')
    wind_reference_height = Float(iotype='in', units='m', desc='reference height')
    alpha = Float(iotype='in', desc='power law exponent')
    wall_thickness = Array(iotype='in', units='m',desc = 'wall thickness of each section')
    number_of_rings = Array(iotype='in',desc = 'number of stiffeners in each section')
    neutral_axis = Float(iotype='in',units='m',desc = 'neutral axis location')
    """Costs inputs."""
    straight_col_cost = Float(3490, iotype='in',units='USD',desc='cost of straight columns in $/ton')
    tapered_col_cost = Float(4720, iotype='in',units='USD',desc='cost of tapered columns in $/ton')
    outfitting_cost = Float(6980, iotype='in',units='USD',desc='cost of tapered columns in $/ton')
    ballast_cost = Float(100, iotype='in',units='USD',desc='cost of tapered columns in $/ton')
    """Additional inputs."""
    stiffener_curve_fit = Bool(iotye='in', desc='flag for using optimized stiffener dimensions or discrete stiffeners')
    stiffener_index = Int(iotype='in',desc='index of stiffener from filtered table')
    number_of_sections = Int(iotype='in',desc='number of sections in the spar')
    outer_diameter = Array(iotype='in', units='m',desc = 'outer diameter of each section')
    elevations = Array(iotype='in', units='m',desc = 'elevations of each section')
    bulk_head = Array(iotype='in',desc = 'N for none, wall_thickness_array for top, B for bottom') 
    material_density = Float(7850.,iotype='in', units='kg/m**3', desc='density of spar material')
    E = Float(200.e9,iotype='in', units='Pa', desc='young"s modulus of spar material')
    nu = Float(0.3,iotype='in', desc='poisson"s ratio of spar material')
    yield_stress = Float(345000000.,iotype='in', units='Pa', desc='yield stress of spar material')
    """Ballast stuff inputs."""
    shell_mass_factor = Float(1.0,iotype='in',desc='shell mass factor')
    bulkhead_mass_factor = Float(1.0,iotype='in',desc='bulkhead mass factor')
    ring_mass_factor = Float(1.0,iotype='in',desc='ring mass factor')
    outfitting_factor = Float(0.06,iotype='in',desc='outfitting factor')
    spar_mass_factor = Float(1.05,iotype='in',desc='spar mass factor')
    permanent_ballast_height = Float(3.,iotype='in',units='m',desc='height of permanent ballast')
    fixed_ballast_height = Float(5.,iotype='in',units='m',desc='height of fixed ballast')
    permanent_ballast_density = Float(4492.,iotype='in',units='kg/m**3',desc='density of permanent ballast')
    fixed_ballast_density = Float(4000.,iotype='in',units='kg/m**3',desc='density of fixed ballast')
    offset_amplification_factor = Float(1.0,iotype='in',desc='amplification factor for offsets')  
    """Inputs from tower_RNA.py."""
    RNA_keel_to_CG = Float(iotype='in',units='m',desc='RNA keel to center of gravity')
    RNA_mass = Float(iotype='in',units='kg',desc='RNA mass')
    tower_mass = Float(iotype='in',units='kg',desc='tower mass')
    tower_center_of_gravity = Float(iotype='in',units='m',desc='tower center of gravity')
    tower_wind_force = Float(iotype='in',units='N',desc='wind force on tower')
    RNA_wind_force = Float(iotype='in',units='N',desc='wind force on RNA')
    RNA_center_of_gravity_x = Float(iotype='in',units='m',desc='RNA center of gravity in x-direction')
    """Inputs from mooring.py."""
    mooring_total_cost = Float(iotype='in',units='USD',desc='total cost for anchor + legs + miscellaneous costs')
    mooring_keel_to_CG = Float(iotype='in',units='m',desc='mooring_keel_to_CG used in spar.py')
    mooring_vertical_load = Float(iotype='in',units='N',desc='mooring vertical load in all mooring lines')
    mooring_horizontal_stiffness = Float(iotype='in',units='N/m',desc='horizontal stiffness of one single mooring line')
    mooring_vertical_stiffness = Float(iotype='in',units='N/m',desc='vertical stiffness of all mooring lines')
    sum_forces_x = Array(iotype='in',units='N',desc='sume of forces in x direction')
    offset_x = Array(iotype='in',units='m',desc='X offsets in discretization')
    damaged_mooring = Array(iotype='in',units='m',desc='range of damaged mooring')
    intact_mooring = Array(iotype='in',units='m',desc='range of intact mooring')
    mooring_mass = Float(iotype='in',units='kg',desc='total mass of mooring')
    """Outputs."""
    flange_compactness = Float(iotype='out',desc = 'check for flange compactness')
    web_compactness = Float(iotype='out',desc = 'check for web compactness')
    VAL = Array(iotype='out',desc = 'unity check for axial load - local buckling')
    VAG = Array(iotype='out',desc = 'unity check for axial load - genenral instability')
    VEL = Array(iotype='out',desc = 'unity check for external pressure - local buckling')
    VEG = Array(iotype='out',desc = 'unity check for external pressure - general instability')
    platform_stability_check = Float(iotype='out',desc = 'check for platform stability')
    heel_angle = Float(iotype='out',desc='heel angle unity check')
    min_offset_unity = Float(iotype='out',desc='minimum offset unity check')
    max_offset_unity = Float(iotype='out',desc='maximum offset unity check')
    total_cost = Float(iotype='out',units='USD',desc='cost of mooring and spar')
    water_ballast_height = Float(iotype='out',units='m',desc='height of water ballast')
    spar_cost = Float(iotype='out',units='USD',desc='cost of mooring and spar')
    outfit_cost = Float(iotype='out',units='USD',desc='cost of mooring and spar')
    ballasts_cost = Float(iotype='out',units='USD',desc='cost of mooring and spar')
    spar_mass = Float(iotype='out',units='kg',desc='mass of spar')
    ballast_mass = Float(iotype='out',units='kg',desc='ballasts mass')
    system_total_mass = Float(iotype='out',units='kg',desc='total mass of spar system')
    shell_mass = Float(iotype='out',units='kg',desc='total mass of spar system')
    bulkhead_mass = Float(iotype='out',units='kg',desc='total mass of spar system')
    stiffener_mass = Float(iotype='out',units='kg',desc='total mass of spar system')
    
    def __init__(self):
        super(Spar,self).__init__()
    
    def execute(self):
        ''' 
        '''
        # assign all varibles 
        gravity = self.gravity
        air_density = self.air_density 
        water_density = self.water_density
        water_depth = self.water_depth
        load_condition = self.load_condition
        significant_wave_height = self.significant_wave_height
        significant_wave_period = self.significant_wave_period
        if significant_wave_height!= 0: 
            significant_wave_height = 1.86*significant_wave_height
            significant_wave_period = 0.71*significant_wave_period
            WAVEL = gravity*significant_wave_period**2/(2*pi)
            WAVEN = 2*pi/WAVEL  
        wind_reference_speed = self.wind_reference_speed
        wind_reference_height = self.wind_reference_height
        alpha = self.alpha 
        material_density = self.material_density
        E = self.E
        nu = self.nu
        yield_stress = self.yield_stress
        permanent_ballast_height = self.permanent_ballast_height 
        permanent_ballast_density = self.permanent_ballast_density
        fixed_ballast_height = self.fixed_ballast_height
        fixed_ballast_density = self.fixed_ballast_density
        RNA_mass = self.RNA_mass
        RNA_kell_to_CG = self.RNA_keel_to_CG
        tower_mass = self.tower_mass
        tower_center_of_gravity = self.tower_center_of_gravity
        tower_wind_force = self.tower_wind_force
        RNA_wind_force = self.RNA_wind_force
        RNA_center_of_gravity_x = self.RNA_center_of_gravity_x
        mooring_vertical_load = self.mooring_vertical_load
        mooring_horizontal_stiffness = self.mooring_horizontal_stiffness
        mooring_vertical_stiffness = self.mooring_vertical_stiffness
        mooring_keel_to_CG = self.mooring_keel_to_CG
        outer_diameter_array = array(self.outer_diameter)
        base_outer_diameters = outer_diameter_array[-1] # base outer diameter
        wall_thickness_array = array(self.wall_thickness)
        end_elevation = array(self.elevations[1:]) # end elevation
        ELS = array(self.elevations[0:-1]) # start elevation
        NSEC = self.number_of_sections
        for i in range(0,NSEC+1):
            if  self.elevations[i] >0:
                ODTW = outer_diameter_array[i+1]
        LB = ELS-end_elevation # lengths of each section
        DRAFT = abs(min(end_elevation))
        FB = ELS [0] # freeboard
        BH = self.bulk_head 
        N = array(self.number_of_rings)
        if self.stiffener_curve_fit: # curve fits
            YNA=self.neutral_axis
            D = 0.0029+1.3345977*YNA
            IR =0.051*YNA**3.7452
            TW = exp(0.88132868+1.0261134*log(IR)-3.117086*log(YNA))
            AR = exp(4.6980391+0.36049717*YNA**0.5-2.2503113/(TW**0.5))
            TFM =1.2122528*YNA**0.13430232*YNA**1.069737
            BF = (0.96105249*TW**-0.59795001*AR**0.73163096)
            IR = 0.47602202*TW**0.99500847*YNA**2.9938134    
        else: # discrete, actual stiffener 
            allStiffeners = full_stiffeners_table()
            stiffener = allStiffeners[self.stiffener_index]
            stiffenerName = stiffener[0]
            AR = convert_units(stiffener[1],'inch**2','m**2')
            D = convert_units(stiffener[2],'inch','m')
            TW = convert_units(stiffener[3],'inch','m')
            BF=  convert_units(stiffener[4],'inch','m')
            TFM = convert_units(stiffener[5],'inch','m')
            YNA = convert_units(stiffener[6],'inch','m')
            self.neutral_axis=YNA
            IR = convert_units(stiffener[7],'inch**4','m**4')
        HW = D - TFM # web height
        SHM,RGM,BHM,SHB,SWF,SWM,SCF,SCM,KCG,KCB=calculateWindCurrentForces(0.,0.,N,AR,BH,outer_diameter_array,NSEC,wall_thickness_array,LB,material_density,DRAFT,end_elevation,ELS,water_density,air_density,gravity,significant_wave_height,significant_wave_period,water_depth,wind_reference_speed,wind_reference_height,alpha)     
        SHBUOY = sum(SHB) # shell buoyancy
        SHMASS = sum(SHM)*self.shell_mass_factor # shell mass - VALUE
        BHMASS = sum(BHM)*self.bulkhead_mass_factor # bulkhead mass - VALUE
        RGMASS = sum(RGM)*self.ring_mass_factor # ring mass - VALUE
        SHRMASS = SHMASS + BHMASS + RGMASS # shell and bulkhead and ring mass - VALUE
        SHRM = array(SHM)+array(BHM)+array(RGM) # # shell and bulkhead and ring mass - ARRAY
        percent_shell_mass = RGMASS/SHMASS *100. 
        outfitting_mass = SHRMASS*self.outfitting_factor
        SMASS = SHRMASS*self.spar_mass_factor + outfitting_mass 
        KCG = dot(SHRM, array(KCG))/SHRMASS # keel to center of gravity
        KB = dot(array(SHB),array(KCB))/SHBUOY  # keel to center of buoyancy 
        BM = ((pi/64)*ODTW**4)/(SHBUOY/water_density) 
        SWFORCE = sum(SWF) # shell wind force 
        SCFORCE = sum(SCF) # shell current force - NOTE: inaccurate; setting an initial value and reruns later
        BVL = pi/4.*(base_outer_diameters-2*wall_thickness_array[-1])**2.  # ballast volume per length
        KGPB = (permanent_ballast_height/2.)+wall_thickness_array[-1] 
        PBM = BVL*permanent_ballast_height*permanent_ballast_density # permanent ballast mass
        KGFB = (fixed_ballast_height/2.)+permanent_ballast_height+wall_thickness_array[-1] 
        FBM = BVL*fixed_ballast_height*fixed_ballast_density # fixed ballast mass
        WPA = pi/4*(ODTW)**2
        KGT = tower_center_of_gravity+FB+DRAFT # keel to center of gravity of tower
        WBM = SHBUOY-SMASS-RNA_mass-tower_mass-mooring_vertical_load/gravity-FBM-PBM # water ballast mass
        WBH = WBM/(water_density*BVL) # water ballast height
        KGWB = WBH/2.+permanent_ballast_height+fixed_ballast_height+wall_thickness_array[-1]
        KGB = (SMASS*KCG+WBM*KGWB+FBM*KGFB+PBM*KGPB+tower_mass*KGT+RNA_mass*RNA_kell_to_CG)/(SMASS+WBM+FBM+PBM+tower_mass+RNA_mass)
        KG = (SMASS*KCG+WBM*KGWB+FBM*KGFB+PBM*KGPB+tower_mass*KGT+RNA_mass*RNA_kell_to_CG+mooring_vertical_load/gravity*mooring_keel_to_CG)/SHBUOY
        GM = KB+BM-KG
        self.platform_stability_check = KG/KB 
        total_mass = SMASS+RNA_mass+tower_mass+WBM+FBM+PBM
        VD = (RNA_wind_force+tower_wind_force+SWFORCE+SCFORCE)/(SMASS+RNA_mass+tower_mass+FBM+PBM+WBM)
        SHM,RGM,BHM,SHB,SWF,SWM,SCF,SCM,KCG,KCB=calculateWindCurrentForces(KG,VD,N,AR,BH,outer_diameter_array,NSEC,wall_thickness_array,LB,material_density,DRAFT,end_elevation,ELS,water_density,air_density,gravity,significant_wave_height,significant_wave_period,water_depth,wind_reference_speed,wind_reference_height,alpha)     
        SCFORCE = sum(SCF)
        # calculate moments 
        RWM = RNA_wind_force*(RNA_kell_to_CG-KG)
        TWM = tower_wind_force*(KGT-KG)
        # costs
        columns_mass = sum(SHM[1::2])+sum(RGM[1::2])+sum(BHM[1::2])
        tapered_mass = sum(SHM[0::2])+sum(RGM[0::2])+sum(BHM[0::2])
        COSTCOL = self.straight_col_cost
        COSTTAP = self.tapered_col_cost
        COSTOUT = self.outfitting_cost
        COSTBAL = self.ballast_cost
        self.spar_cost = COSTCOL*columns_mass/1000. + COSTTAP*tapered_mass/1000.
        self.outfit_cost = COSTOUT*outfitting_mass/1000.
        self.ballasts_cost = COSTBAL*(FBM+PBM)/1000.
        self.total_cost =self.spar_cost+self.outfit_cost+self.ballasts_cost+self.mooring_total_cost

        ##### SIZING TAB #####    
        # [TOP MASS(RNA+TOWER)]
        top_mass = RNA_mass+tower_mass 
        KG_top = (RNA_mass*RNA_kell_to_CG+tower_mass*KGT)
        # [INERTIA PROPERTIES - LOCAL]
        I_top_loc = (1./12.)*top_mass*KG_top**2
        I_hull_loc = (1./12.)*SMASS*(DRAFT+FB)**2
        I_WB_loc = (1./12.)*WBM*WBH**2
        I_FB_loc = (1./12.)*FBM*fixed_ballast_height**2
        I_PB_loc = (1./12.)*PBM*permanent_ballast_height**2
        # [INERTIA PROPERTIES - SYSTEM]
        I_top_sys = I_top_loc + top_mass*(KG_top-KG)**2
        I_hull_sys = I_hull_loc + SMASS*(KCG-KG)**2
        I_WB_sys = I_WB_loc + WBM*(KGWB-KGB)**2 
        I_FB_sys = I_FB_loc + FBM*(KGFB-KGB)**2
        I_PB_sys = I_PB_loc + PBM*(KGPB-KGB)**2
        I_total = I_top_sys + I_hull_sys + I_WB_sys + I_FB_sys + I_PB_sys
        I_yaw =  total_mass*(base_outer_diameters/2.)**2
        # [ADDED MASS]
        surge = (pi/4.)*base_outer_diameters**2*DRAFT*water_density
        heave = (1/6.)*water_density*base_outer_diameters**3
        pitch = (surge*((KG-DRAFT)-(KB-DRAFT))**2+surge*DRAFT**2/12.)*I_total
        # [OTHER SYSTEM PROPERTIES]
        r_gyration = (I_total/total_mass)**0.5
        CM = (SMASS*KCG+WBM*KGWB+FBM*KGFB+PBM*KGPB)/(SMASS+WBM+FBM+PBM)
        surge_period = 2*pi*((total_mass+surge)/mooring_horizontal_stiffness)**0.5
        # [PLATFORM STIFFNESS]
        K33 = water_density*gravity*(pi/4.)**ODTW**2+mooring_vertical_stiffness  #heave
        K44 = abs(water_density*gravity*((pi/4.)*(ODTW/2.)**4-(KB-KG)*SHBUOY/water_density)) #roll
        K55 = abs(water_density*gravity*((pi/4.)*(ODTW/2.)**4-(KB-KG)*SHBUOY/water_density)) #pitch
        # [PERIOD]
        T_surge = 2*pi*((total_mass+surge)/mooring_horizontal_stiffness)**0.5
        T_heave = 2*pi*((total_mass+heave)/K33)**0.5
        K_pitch = GM*SHBUOY*gravity
        T_pitch = 2*pi*(pitch/K_pitch)**0.5
        F_total = RNA_wind_force+tower_wind_force+sum(SWF)+sum(SCF)
        sum_FX = self.sum_forces_x
        X_Offset = self.offset_x
        if np.isnan(sum_FX).any() or sum_FX[-1] > (-F_total/1000.):
            self.max_offset_unity = 10.
            self.min_offset_unity = 10.
        else:
            for j in range(1,len(sum_FX)): 
                if sum_FX[j]< (-F_total/1000.): 
                    X2 = sum_FX[j]
                    X1 = sum_FX[j-1]
                    Y2 = X_Offset[j]
                    Y1 = X_Offset[j-1]
            max_offset = (Y1+(-F_total/1000.-X1)*(Y2-Y1)/(X2-X1))*self.offset_amplification_factor
            i=0
            while sum_FX[i]> (F_total/1000.):
                i+=1
            min_offset = (X_Offset[i-1]+(F_total/1000.-sum_FX[i-1])*(X_Offset[i]-X_Offset[i-1])/(sum_FX[i]-sum_FX[i-1]))*self.offset_amplification_factor
        # unity checks! 
            if self.load_condition == 'E': 
                self.max_offset_unity = max_offset/self.damaged_mooring[1]
                self.min_offset_unity = min_offset/self.damaged_mooring[0]
            elif self.load_condition == 'N': 
                self.max_offset_unity = max_offset/self.intact_mooring[1]
                self.min_offset_unity = min_offset/self.intact_mooring[0]
        M_total = RWM+TWM+sum(SWM)+sum(SCM)+(-F_total*(mooring_keel_to_CG-KG))+(RNA_mass*gravity*-RNA_center_of_gravity_x)
        self.heel_angle = (M_total/K_pitch)*180./pi
        ##### API BULLETIN #####    
        # shell data
        RO = outer_diameter_array/2.  # outer radius 
        R = RO-wall_thickness_array/2. # radius to centerline of wall/mid fiber radius 
        # ring data 
        LR = LB/(N+1.) # number of ring spacing
        #shell and ring data
        RF = RO - HW  # radius to flange
        MX = LR/(R*wall_thickness_array)**0.5  # geometry parameter
        # effective width of shell plate in longitudinal direction 
        LE=np.array([0.]*NSEC)
        for i in range(0,NSEC):
            if MX[i] <= 1.56: 
                LE[i]=LR[i]
            else: 
                LE = 1.1*(2*R*wall_thickness_array)**0.5+TW 
        # ring properties with effective shell plate
        AER = AR+LE*wall_thickness_array  # cross sectional area with effective shell 
        YENA = (LE*wall_thickness_array*wall_thickness_array/2 + HW*TW*(HW/2+wall_thickness_array) + TFM*BF*(TFM/2+HW+wall_thickness_array))/AER 
        IER = IR+AR*(YNA+wall_thickness_array/2.)**2*LE*wall_thickness_array/AER+LE*wall_thickness_array**3/12. # moment of inertia
        RC = RO-YENA-wall_thickness_array/2. # radius to centroid of ring stiffener 
        # set loads (0 mass loads for external pressure) 
        MBALLAST = PBM + FBM + WBM # sum of all ballast masses
        W = (RNA_mass + tower_mass + MBALLAST + SMASS) * gravity
        P = water_density * gravity* abs(end_elevation)  # hydrostatic pressure at depth of section bottom 
        if significant_wave_height != 0: # dynamic head 
            DH = significant_wave_height/2*(np.cosh(WAVEN*(water_depth-abs(end_elevation)))/np.cosh(WAVEN*water_depth)) 
        else: 
            DH = 0 
        P = P + water_density*gravity*DH # hydrostatic pressure + dynamic head
        GF = self.gust_factor
        #-----RING SECTION COMPACTNESS (SECTION 7)-----#
        self.flange_compactness = (0.5*BF/TFM)/(0.375*(E/yield_stress)**0.5)
        self.web_compactness = (HW/TW)/((E/yield_stress)**0.5)
        #-----PLATE AND RING STRESS (SECTION 11)-----#
        # shell hoop stress at ring midway 
        Dc = E*wall_thickness_array**3/(12*(1-nu**2))  # parameter D 
        BETAc = (E*wall_thickness_array/(4*RO**2*Dc))**0.25 # parameter beta 
        TWS = AR/HW
        dum1 = BETAc*LR
        KT = 8*BETAc**3 * Dc * (np.cosh(dum1) - np.cos(dum1))/ (np.sinh(dum1) + np.sin(dum1))
        KD = E * TWS * (RO**2 - RF**2)/(RO * ((1+nu) * RO**2 + (1-nu) * RF**2))
        dum = dum1/2. 
        PSIK = 2*(np.sin(dum) * np.cosh(dum) + np.cos(dum) * np.sinh(dum)) / (np.sinh(dum1) + np.sin(dum1))
        PSIK = PSIK.clip(min=0) # psik >= 0; set all negative values of psik to zero
        SIGMAXA = -W/(2*pi*R*wall_thickness_array)
        PSIGMA = P + (nu*SIGMAXA*wall_thickness_array)/RO
        PSIGMA = np.minimum(PSIGMA,P) # PSIGMA has to be <= P
        dum = KD/(KD+KT)
        KTHETAL = 1 - PSIK*PSIGMA/P*dum
        FTHETAS = KTHETAL*P*RO/wall_thickness_array
        # shell hoop stress at ring 
        KTHETAG = 1 - (PSIGMA/P*dum)
        FTHETAR = KTHETAG*P*RO/wall_thickness_array
        #-----LOCAL BUCKLING (SECTION 4)-----# 
        # axial compression and bending 
        ALPHAXL = 9/(300+(2*R)/wall_thickness_array)**0.4
        CXL = (1+(150/((2*R)/wall_thickness_array))*(ALPHAXL**2)*(MX**4))**0.5
        FXEL = CXL * (pi**2 * E / (12 * (1 - nu**2))) * (wall_thickness_array/LR)**2 # elastic 
        FXCL=np.array(NSEC*[0.])
        for i in range(0,len(FXEL)):
            FXCL[i] = plasticityRF(FXEL[i],yield_stress) # inelastic 
        # external pressure
        BETA = np.array([0.]*NSEC)
        ALPHATHETAL = np.array([0.]*NSEC)
        global ZM
        ZM = 12*(MX**2 * (1-nu**2)**.5)**2/pi**4
        for i in range(0,NSEC):
            f=lambda x:x**2*(1+x**2)**4/(2+3*x**2)-ZM[i]
            ans = roots(f, 0.,15.)
            ans_array = np.asarray(ans)
            is_scalar = False if ans_array.ndim>0 else True
            if is_scalar: 
                BETA[i] = ans 
            else: 
                BETA[i] = float(min(ans_array))
            if MX[i] < 5:
                ALPHATHETAL[i] = 1
            elif MX[i] >= 5:
                ALPHATHETAL[i] = 0.8  
        n = np.round(BETA*pi*R/LR) # solve for smallest whole number n 
        BETA = LR/(pi*R/n)
        left = (1+BETA**2)**2/(0.5+BETA**2)
        right = 0.112*MX**4 / ((1+BETA**2)**2*(0.5+BETA**2))
        CTHETAL = (left + right)*ALPHATHETAL 
        FREL = CTHETAL * pi**2 * E * (wall_thickness_array/LR)**2 / (12*(1-nu**2)) # elastic
        FRCL=np.array(NSEC*[0.])
        for i in range(0,len(FREL)):
            FRCL[i] = plasticityRF(FREL[i],yield_stress) # inelastic 
        #-----GENERAL INSTABILITY (SECTION 4)-----# 
        # axial compression and bending 
        AC = AR/(LR*wall_thickness_array) # Ar bar 
        ALPHAX = 0.85/(1+0.0025*(outer_diameter_array/wall_thickness_array))
        ALPHAXG = np.array([0.]*NSEC)
        for i in range(0,NSEC):
            if AC[i] >= 0.2 :
                ALPHAXG[i] = 0.72
            elif AC[i] > 0.06 and AC[i] <0.2:
                ALPHAXG[i] = (3.6-0.5*ALPHAX[i])*AC[i]+ALPHAX[i]
            else: 
                ALPHAXG[i] = ALPHAX[i]
        FXEG = ALPHAXG * 0.605 * E * wall_thickness_array / R * (1 + AC)**0.5 # elastic
        FXCG = np.array(NSEC*[0.])
        for i in range(0,len(FXEG)):
            FXCG[i] = plasticityRF(FXEG[i],yield_stress) # inelastic  
        # external pressure 
        ALPHATHETAG = 0.8
        LAMBDAG = pi * R / LB 
        k = 0.5 
        PEG = np.array([0.]*NSEC)
        for i in range(0,NSEC):
            t = wall_thickness_array[i]
            r = R[i]
            lambdag = LAMBDAG[i]
            ier = IER[i]
            rc = RC[i]
            ro = RO[i]
            lr = LR[i]
            def f(x,E,t,r,lambdag,k,ier,rc,ro,lr):
                return E*(t/r)*lambdag**4/((x**2+k*lambdag**2-1)*(x**2+lambdag**2)**2) + E*ier*(x**2-1)/(lr*rc**2*ro)   
            x0 = [2]
            m = float(fmin(f, x0, xtol=1e-3, args=(E,t,r,lambdag,k,ier,rc,ro,lr))) # solve for n that gives minimum P_eG
            PEG[i] = f(m,E,t,r,lambdag,k,ier,rc,ro,lr)
        ALPHATHETAG = 0.8 #adequate for ring stiffeners 
        FREG = ALPHATHETAG*PEG*RO*KTHETAG/wall_thickness_array # elastic 
        FRCG = np.array(NSEC*[0.])
        for i in range(0,len(FREG)):
            FRCG[i] = plasticityRF(FREG[i],yield_stress) # inelastic  
        # General Load Case
        NPHI = W/(2*pi*R)
        NTHETA = P * RO 
        K = NPHI/NTHETA 
        #-----Local Buckling (SECTION 6) - Axial Compression and bending-----# 
        C = (FXCL + FRCL)/yield_stress -1
        KPHIL = 1
        CST = K * KPHIL /KTHETAL 
        FTHETACL = np.array([0.]*NSEC)
        bnds = (0,None)
        for i in range(0,NSEC):
            cst = CST[i]
            fxcl = FXCL[i]
            frcl = FRCL[i]
            c = C[i]
            x = Symbol('x')
            ans = solve((cst*x/fxcl)**2 - c*(cst*x/fxcl)*(x/frcl) + (x/frcl)**2 - 1, x)
            FTHETACL[i] =  float(min([a for a in ans if a>0]))
        FPHICL = CST*FTHETACL
        #-----General Instability (SECTION 6) - Axial Compression and bending-----# 
        C = (FXCG + FRCG)/yield_stress -1
        KPHIG = 1
        CST = K * KPHIG /KTHETAG 
        FTHETACG = np.array([0.]*NSEC)
        for i in range(0,NSEC):
            cst = CST[i]
            fxcg = FXCG[i]
            frcg = FRCG[i]
            c = C[i]
            x = Symbol('x',real=True)
            ans = solve((cst*x/fxcg)**2 - c*(cst*x/fxcg)*(x/frcg) + (x/frcg)**2 - 1, x)
            FTHETACG[i] =  float(min([a for a in ans if a>0]))
        FPHICG = CST*FTHETACG
        #-----Allowable Stresses-----# 
        # factor of safety
        FOS = 1.25
        if load_condition == 'N' or load_condition == 'n': 
            FOS = 1.65
        FAL = np.array([0.]*NSEC)
        FAG = np.array([0.]*NSEC)
        FEL = np.array([0.]*NSEC)
        FEG = np.array([0.]*NSEC)
        for i in range(0,NSEC):
            # axial load    
            FAL[i] = FPHICL[i]/(FOS*calcPsi(FPHICL[i],yield_stress))
            FAG[i] = FPHICG[i]/(FOS*calcPsi(FPHICG[i],yield_stress))
            # external pressure
            FEL[i] = FTHETACL[i]/(FOS*calcPsi(FTHETACL[i],yield_stress))
            FEG[i] = FTHETACG[i]/(FOS*calcPsi(FTHETACG[i],yield_stress))
        # unity check 
        self.VAL = abs(SIGMAXA / FAL)
        self.VAG = abs(SIGMAXA / FAG)
        self.VEL = abs(FTHETAS / FEL)
        self.VEG = abs(FTHETAS / FEG)
        self.water_ballast_height = WBH
        
         
        
        print 'surge period: ', T_surge
        print 'heave period: ', T_heave
        print 'pitch stiffness: ', K_pitch
        print 'pitch period: ', T_pitch
        print 'YNA: ', YNA
        print 'number of stiffeners: ',self.number_of_rings
        print 'wall thickness: ',self.wall_thickness
        print 'VAL: ',self.VAL
        print 'VAG: ',self.VAG
        print 'VEL: ',self.VEL
        print 'VEG: ',self.VEG
        print 'web compactness: ',self.web_compactness
        print 'flange compactness: ',self.flange_compactness
        print 'heel angle: ', self.heel_angle
        print 'outer diameters: ', self.outer_diameter
        self.spar_mass = SHRMASS
        self.ballast_mass = PBM + FBM + WBM
        self.system_total_mass = SHRMASS + PBM + FBM + WBM + self.mooring_mass
        self.shell_mass = SHMASS 
        self.bulkhead_mass = BHMASS
        self.stiffener_mass = RGMASS
        print 'spar mass: ', self.spar_mass
        print 'shell mass: ', self.shell_mass
        print 'bulkhead mass: ', self.bulkhead_mass
        print 'stiffener mass: ', self.stiffener_mass
#-----------------------------------------------------------------