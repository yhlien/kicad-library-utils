# -*- coding: utf-8 -*-

from __future__ import division


# math and comments from Michal script
# https://github.com/michal777/KiCad_Lib_Check

from rules.klc_constants import *
from rules.rule import *

class Rule(KLCRule):
    """
    Create the methods check and fix to use with the kicad_mod files.
    """
    def __init__(self, module, args):
        super(Rule, self).__init__(module, args, 'Rule 7.4', "Fabrication layer requirements")

    # Check for presence of component value
    def checkMissingValue(self):
        mod = self.module
        
        val = mod.value
        
        errors = []
        
        if not val['value'] == mod.name:
            errors.append("Value text should match footprint name:")
            errors.append("Value text is '{v}', expected: '{n}'".format(
                v = val['value'],
                n = mod.name))
        
        # Check for presense of 'value'
        if val['layer'] not in ['F.Fab', 'B.Fab']:
            errors.append("Component value is on layer {lyr} but should be on F.Fab or B.Fab".format(lyr=val['layer']))
        if val['hide']:
            errors.append("Component value is hidden (should be set to visible)")
        if val['font']['height'] != KLC_TEXT_SIZE:
            errors.append("Value label has a height of {1}mm (expected: {0}mm)".format(KLC_TEXT_SIZE, val['font']['height']))
        if val['font']['height'] != KLC_TEXT_SIZE:
            errors.append("Value label has a width of {1}mm (expected: {0}mm)".format(KLC_TEXT_SIZE, val['font']['width']))
        if val['font']['thickness'] != KLC_TEXT_THICKNESS:
            errors.append("Value label has a thickness of {1}mm (expected: {0}mm)".format(KLC_TEXT_THICKNESS, val['font']['thickness']))

        if len(errors) > 0:
            self.error("Value Label Errors")
            for err in errors:
                self.errorExtra(err)
            
        return len(errors) > 0
            
    def checkMissingLines(self):
        if len(self.f_fabrication_all) + len(self.b_fabrication_all) == 0:
            self.error("No drawings found on fabrication layer")
            return True
            
        return False
        
    def getSecondRef(self):
        texts = self.module.userText
        
        ref = None
        
        count = 0
        
        for text in texts:
            if text['user'] == '%R':
                ref = text
                count += 1
                
        self.multiple_second_ref = count > 1
                
        return ref
        
    # Check that there is a second ref '%R' on the fab layer
    def checkSecondRef(self):
        
        ref = self.getSecondRef()
        
        if not ref:
            self.error("Second Reference Designator missing")
            self.errorExtra("Add RefDes to F.Fab layer with '%R'")
            return True
            
        # Check that ref exists
        if ref['layer'] not in ['F.Fab', 'B.Fab']:
            self.error("Reference designator found on layer '{lyr}', expected '{exp}'".format(
                lyr = ref['layer'],
                exp = 'F.Fab'))
            return True
            
        # Check ref size
        font = ref['font']
        
        errors = []
        
        fh = font['height']
        fw = font['width']
        ft = font['thickness']
        
        # Font height 
        if not fh == fw:
            errors.append("RefDes aspect ratio should be 1:1")
            
        if fh < KLC_TEXT_SIZE_MIN or fh > KLC_TEXT_SIZE_MAX:
            errors.append("RefDes text size ({x}mm) is outside allowed range [{y}mm - {z}mm]".format(
                x = fh,
                y = KLC_TEXT_SIZE_MIN,
                z = KLC_TEXT_SIZE_MAX))
                
        # Font thickness
        if ft < KLC_TEXT_THICKNESS_MIN or ft > KLC_TEXT_THICKNESS_MAX:
            errors.append("RefDes text thickness ({x}mm) is outside allowed range [{y}mm - {z}mm]".format(
                x = ft,
                y = KLC_TEXT_SIZE_MIN,
                z = KLC_TEXT_SIZE_MAX))
            
        # Check position / orientation
        pos = ref['pos']
        
        #if not pos['orientation'] == 0:
        #    errors.append("RefDes on F.Fab layer should be horizontal (no rotation)")
            
        if len(errors) > 0:
            self.error("RefDes errors")
            for err in errors:
                self.errorExtra(err)
            
        return len(errors) > 0
    
    # Check fab line widths
    def checkIncorrectWidth(self):
        self.bad_fabrication_width = []
        for graph in (self.f_fabrication_all + self.b_fabrication_all):
            if graph['width'] < KLC_FAB_WIDTH_MIN or graph['width'] > KLC_FAB_WIDTH_MAX:
                self.bad_fabrication_width.append(graph)
                
        msg = False
    
        if len(self.bad_fabrication_width) > 0:
            self.error("Some fabrication layer lines have a width outside allowed range of [{x}mm - {y}mm]".format(
                x = KLC_FAB_WIDTH_MIN,
                y = KLC_FAB_WIDTH_MAX))
                
            for g in self.bad_fabrication_width:
                self.errorExtra(graphItemString(g, layer=True, width=True))
        
        return len(self.bad_fabrication_width) > 0
        
    def check(self):
        """
        Proceeds the checking of the rule.
        The following variables will be accessible after checking:
            * f_fabrication_all
            * b_fabrication_all
            * f_fabrication_lines
            * b_fabrication_lines
            * bad_fabrication_width
        """
        
        self.missing_value = False
        self.missing_lines = False
        self.incorrect_width = False
        self.multiple_second_ref = False
        self.missing_second_ref = False
        
        module = self.module
        self.f_fabrication_all = module.filterGraphs('F.Fab')
        self.b_fabrication_all = module.filterGraphs('B.Fab')

        self.f_fabrication_lines = module.filterLines('F.Fab')
        self.b_fabrication_lines = module.filterLines('B.Fab')
                
        self.missing_value = self.checkMissingValue()
        self.missing_lines = self.checkMissingLines()
        self.incorrect_width = self.checkIncorrectWidth()
        self.missing_second_ref = self.checkSecondRef()
        
        if self.multiple_second_ref:
            self.error("Mutliple RefDes markers found with text '%R'")
                
        return any([
                    self.missing_value,
                    self.missing_lines,
                    self.incorrect_width,
                    self.missing_second_ref,
                    ])

    def fix(self):
        """
        Proceeds the fixing of the rule, if possible.
        """
        module = self.module
        if self.incorrect_width:
            self.info("Setting F.Fab lines to correct width")
            for graph in self.bad_fabrication_width:
                graph['width'] = KLC_FAB_WIDTH
                
        if self.missing_value:
            self.info("Fixing 'Value' text on F.Fab layer")
            module.value['value'] = module.name
            module.value['layer'] = 'F.Fab'
            module.value['font']['height'] = KLC_TEXT_SIZE
            module.value['font']['width'] = KLC_TEXT_SIZE
            module.value['font']['thickness'] = KLC_TEXT_THICKNESS
            
        if self.missing_second_ref:
            # Best-guess for pos is midpoint the footprint bounds
            bounds = module.geometricBoundingBox('F.Fab')
            
            # Can't get fab outline? Use pads
            if not bounds.valid:
                bounds = module.overpadsBounds()
            
            if bounds.valid:
                pos = bounds.center
                
                # Ensure position is on grid
                pos['x'] = round(mapToGrid(pos['x'],0.001),4)
                pos['y'] = round(mapToGrid(pos['y'],0.001),4)
                
                # these numbers were a litle bit "trial and error"
                text_size = 4.0
                
                if bounds.width < text_size:
                    text_size = 0.9 * bounds.width
                    
                text_size = round(text_size / 4, 1)
                
                # Minimum Size Limit
                # KLC_TEXT_SIZE_MIN is 0.25mm
                # But, this is very small and our "best guess" should be conservative
                
                MIN = 0.5
                
                # Limit to smallest KLC value
                if text_size < MIN:
                    text_size = MIN
                
                text_line = round(0.15 * text_size, 3)
            # Still can't get bounds? Use 0,0
            else:
                pos = {'x': 0, 'y': 0}
                text_size = 1.0
                text_line = 0.15
                
            self.info("Adding second RefDes to F.Fab layer @ ({x},{y})".format(
                x = pos['x'],
                y = pos['y']))
                
            font = {'thickness': text_line, 'height': text_size, 'width': text_size}
            
            module.addUserText('%R',
                {'pos': pos,
                 'font': font,
                 'layer': 'F.Fab'
                    
                })
            