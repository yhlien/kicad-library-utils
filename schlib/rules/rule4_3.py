# -*- coding: utf-8 -*-

from rules.rule import *

class Rule(KLCRule):
    """
    Create the methods check and fix to use with the kicad lib files.
    """
    def __init__(self, component):
        super(Rule, self).__init__(component, 'Rule 4.3 - Pin stacking', 'Mismatching pins cannot be placed in the same location')
        self.different_names=False
        self.NC_stacked=False
        self.different_types=False
        self.only_one_visible=False

    def stackStr(self, stack):
        multi_unit = int(self.component.definition['unit_count']) > 1
        unit_str = " (unit {u})".format(stack['u']) if multi_unit else ""
        
        # WHY are pins flipped vertically? Mega sad face :(
        return "Pinstack @ ({x},{y}){u}".format(
            x = int(stack['x']),
            y = -1 * int(stack['y']),
            u = unit_str)
        
    def pinStr(self, pin):
        multi_unit = int(self.component.definition['unit_count']) > 1
        
        if multi_unit:
            unit = pin['unit']
        else:
            unit = None
            
        return pinString(pin, unit)
        
    def check(self):
    
        # List of lists of pins that are entirely duplicated
        self.duplicated_pins = []
        
        pin_locations = []
        
        for pin in self.component.pins:
            
            # To be "identical", all following properties much be the same
            
            pinx = pin['posx']    # x coordinate
            piny = pin['posy']    # y coordinate
            pinu = pin['unit']    # unit (for multi-unit parts)
            pinc = pin['convert'] # convert (de morgan)
            
            dupe = False
            
            for loc in pin_locations:
            
                locx = loc['x']
                locy = loc['y']
                locu = loc['u']
                locc = loc['c']
                
                if pinx == locx and piny == locy and pinu == locu and pinc == locc:
                    loc['pins'].append(pin)
                    dupe = True
                    
            if not dupe:
                new_loc = {'x': pinx, 'y': piny, 'u': pinu, 'c': pinc}
                new_loc['pins'] = [pin]
                pin_locations.append(new_loc)
                    
        err = False
                    
        for loc in pin_locations:
            if len(loc['pins']) > 1:
                
                pin_units = set()
                pin_nums = set()
                pin_names = set()
                pin_etypes = set()
                
                vis_pin_count = 0
                
                for pin in loc['pins']:
                    pin_nums.add(pin['num'])
                    pin_names.add(pin['name'])
                    pin_units.add(pin['unit'])
                    pin_etypes.add(pin['electrical_type'])
                    
                    # Add visibile pins
                    if not pin['pin_type'].startswith('N'):
                        vis_pin_count += 1
                    
                    # NC pins should never be stacked
                    if pin['electrical_type'] == 'N':
                        self.error("NC {pin} @ ({x},{y})is stacked on other pins".format(
                            pin = self.pinStr(pin),
                            x = pin['posx'],
                            y = -1*int(pin['posy'])))
                        err = True
                        self.NC_stacked=True
                            
                # Fewer pin numbers than pins
                if len(pin_nums) < len(loc['pins']):
                    self.error("Duplicate pins @ ({x},{y})".format(
                        x = loc['x'],
                        y = -1 * int(loc['y'])))
                    err = True
                    for pin in loc['pins']: 
                        self.errorExtra(self.pinStr(pin))
                            
                    # If ALL pins are identical, go to next group (no further checks needed)
                    if len(pin_nums) == len(pin_names) == len(pin_units) == 1:
                        self.duplicated_pins.append([pin for pin in loc['pins']])
                        continue
                            
                # Different names!
                if len(pin_names) > 1:
                    self.error(self.stackStr(loc) + " have different names")
                    err = True
                    for pin in loc['pins']:
                        self.errorExtra(self.pinStr(pin))
                        self.different_names=True
                            
                # Different types!
                if len(pin_etypes) > 1:
                    self.error(self.stackStr(loc) + " have different types")
                    err = True
                    for pin in loc['pins']:
                        self.errorExtra("{pin} : {etype}".format(
                            pin = self.pinStr(pin),
                            etype = pinElectricalTypeToStr(pin['electrical_type'])))
                        self.different_types=True
            
                # Only one pin should be visible
                if not vis_pin_count == 1:
                    self.error(self.stackStr(loc) + " must have exactly one (1) invisible pin")
                    err = True
                    for pin in loc['pins']:
                        self.errorExtra("{pin} is {vis}".format(
                            pin = self.pinStr(pin),
                            vis = 'INVISIBLE' if pin['pin_type'].startswith('N') else 'VISIBLE'))
                        self.only_one_visible=True
        return err
                    
    def fix(self):
        # Delete duplicate pins
        if len(self.duplicated_pins) > 0:
            self.info("Removing duplicate pins")
            
            for pin_groups in self.duplicated_pins:
                # Leave first pin and delete all others
                pin = pin_groups[0]
                
                count = 0
                # Iterate through component pins
                i = 0
                while i < len(self.component.drawOrdered):
                    
                    el = self.component.drawOrdered[i]
                    if not el[0] == 'X': # Pins
                        i += 1 
                        continue
                    
                    p_test = el[1]
                
                    # All these keys must be identical!
                    keys = ['name','num','unit','posx','posy','convert']
                    
                    # Found duplicate
                    if all([p_test[key] == pin[key] for key in keys]):
                        count += 1
                        # Skip the first instance, delete all others
                        if count > 1:
                            del self.component.drawOrdered[i]
                            self.info("Deleting {pin} @ ({x},{y})".format(
                                pin = self.pinStr(pin),
                                x = pin['posx'],
                                y = pin['posy']))
                            continue
                    i += 1
                    
        if self.different_names:
            self.info("FIX for 'different pin names' not supported (yet)! Please fix manually.")
        if self.NC_stacked:
            self.info("FIX for 'NC pins stacked' not supported! Please fix manually.")
        if self.different_types:
            self.info("FIX for 'different pin types' not supported (yet)! Please fix manually.")
        if self.only_one_visible:
            self.info("FIX for 'only one pin in a pin stack is visible' not supported (yet)! Please fix manually.")