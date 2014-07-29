import ast
import numbers
from math import floor

from sympy.physics import units
from sympy.physics.units import Unit
from sympy.core.numbers import Number as sympyNumber

from stata_dta import Dta117
try:
    from stata import st_format
    IN_STATA = True
except ImportError:
    IN_STATA = False


class SyntaxChecker(ast.NodeVisitor):
    allowed = set(['Module', 'Expr', 'Load', 'Num', 'Name', 
                    'BinOp', 'Mult', 'Div', 'Pow'])

    def check(self, syntax):
        tree = ast.parse(syntax)
        self.visit(tree)
            
    def generic_visit(self, node):
        if type(node).__name__ not in self.allowed:
            raise SyntaxError("{} is not allowed!".format(type(node).__name__))
        else:
            ast.NodeVisitor.generic_visit(self, node)


class RewriteNames(ast.NodeTransformer):
    def _get_unitName(self, id):
        global units
        
        if hasattr(units, id): return id
        if hasattr(units, id.lower()): return id.lower()
        candidates = units.find_unit(id)
        if len(candidates) == 0:
            raise ValueError("cannot find unit with name " + id)
        if len(candidates) > 1:
            raise ValueError("multiple possible units found for " + id)
        return candidates[0]
        
    def visit_Name(self, node):
        if node.id == 'newUnit' and isinstance(node.ctx, ast.Store):
            return node
        return ast.copy_location(
            ast.Attribute(
                value = ast.Name(id = 'units', ctx = ast.Load()), 
                attr = self._get_unitName(node.id), 
                ctx = ast.Load()
            ), node)

#unitsType = type(units.m)


class UnitsRatio():
    def __init__(self, numer, denom):
        self.numer = numer
        self.denom = denom
        
    def __repr__(self):
        return "( " + repr(self.numer) + " ) / ( " + repr(self.denom) + " )"
        
    def __mul__(self, other):
        if isinstance(other, UnitsRatio):
            #return (self.numer * other.numer) / (self.denom * other.denom)
            #return UnitsRatio(self.numer * other.numer, self.denom * other.denom)
            numerPart = (self.numer / other.denom).as_numer_denom()
            denomPart = (other.numer / self.denom).as_numer_denom()
            
            newNumer = numerPart[0] * denomPart[0]
            newDenom = numerPart[1] * denomPart[1]
            
            simplified = newNumer / newDenom
            if isinstance(simplified, sympyNumber) or isinstance(simplified, numbers.Number):
                return float(simplified)
            
            if isinstance(newDenom, sympyNumber) or isinstance(newDenom, numbers.Number):
                return newNumer
            
            return UnitsRatio(newNumer, newDenom)
        else:
            numerPart = self.numer.as_numer_denom()
            denomPart = (other / self.denom).as_numer_denom()
            
            newNumer = numerPart[0] * denomPart[0]
            newDenom = numerPart[1] * denomPart[1]
            
            if isinstance(newDenom, sympyNumber) or isinstance(newDenom, numbers.Number):
                return newNumer
            
            return UnitsRatio(newNumer, newDenom)
        
    __rmul__ = __mul__
            
    def __rtruediv__(self, other):
        #global unitsType
        if isinstance(other, UnitsRatio):
            a = other.numer / self.numer
            b = self.denom / other.denom
            return a * b
            #if isinstance(a, unitsType) and isinstance(b, unitsType):
            #    return  a * b
            #return UnitsRatio(other.numer * self.denom, other.denom * self.numer)
        else:
            return UnitsRatio(other * self.denom, self.numer)
        
    def __truediv__(self, other):
        #global unitsType
        if isinstance(other, UnitsRatio):
            a = self.numer / other.numer
            b = other.denom / self.denom
            return a * b
            #if isinstance(a, unitsType) and isinstance(b, unitsType):
            #    return  a * b
            #return UnitsRatio(self.numer * other.denom, self.denom * other.numer)
        else:
            return UnitsRatio(self.numer, self.denom * other)
            
    def reduce(self):
        return self.numer / self.denom


class CountUnit(Unit):
    pass


class CurrencyUnit():
    def __init__(self, currency, time):
        self.currency = currency
        self.time = time
        
    def _getTimeFactor(self, newTime):
        pass
        
    def _getCurrencyFactor(self, newCurrency):
        pass

units.gal = units.gallon = units.gallons = 231 * units.inch**3
units.quart = units.quarts = units.gallon / 4 # quart is mis-defined in sympy units
units.mpg = UnitsRatio(units.mi, units.gallon)
units.gpm = UnitsRatio(units.gallon, units.mi)
units.lp100km = units.l_per_100km = units.L_per_100km = UnitsRatio(units.liter, 100 * units.kilometer)
units.lb = units.lbs = units.pound

# count units
units.dozen = units.dozens = 12
units.count = 1
units.gross = 144
units.thou = units.thousand = 1000
units.M = units.million = units.millions = 10**6
units.B = units.billion = units.billions = 10**9


class UDta(Dta117):
    #def __init__(self, *args, **kwargs):
    #    Dta.__init__(self, *args, **kwargs)

    def _get_unit(self, unit_repr):
        unit_repr = unit_repr.replace("^", "**")
        
        ## check that unit_repr only contains allowed stuff
        #wasError = False
        #try:
        #    SyntaxChecker().check(unit_repr)
        #except SyntaxError:
        #    wasError = True
        #
        ## if error is raised in SyntaxChecker, the traceback can be long;
        ## re-raising like this is an easy way to get a shorter accurate traceback
        #if wasError:
        #    raise SyntaxError('illegal syntax in unit str')
        
        # the following might only work in Python 3.3+;
        # the commented-out code above should work in other Python versions
        
        # check that unit_repr only contains allowed stuff
        #wasError = False
        try:
            SyntaxChecker().check(unit_repr)
        except SyntaxError:
            raise SyntaxError('illegal syntax in unit str') from None
    
        # augment tree with assignment and replace any unit name with units.name
        tree = ast.parse('newUnit = ' + unit_repr)
        tree = RewriteNames().visit(tree)
        tree = ast.fix_missing_locations(tree)
        
        # compile in separate namespace
        a = compile(tree, '', 'exec')
        newSpace = {'units': units}
        exec(a, newSpace)
        
        return newSpace['newUnit']
        
    def _check_comparability(self, oldUnit, newUnit):
        """check whether two units are comparable, and return factor if so"""
        # relationship should be direct or inverse
        # first, check direct by dividing
        comp = oldUnit / newUnit
        #if all(isinstance(atom, sympyNumber) 
        #        or isinstance(atom, numbers.Number) 
        #        or isinstance(atom, CountUnit) for atom in comp.atoms()):
        if isinstance(comp, sympyNumber) or isinstance(comp, numbers.Number):
            return float(comp), "direct"
        # check whether inversely related by multiplying
        comp = oldUnit * newUnit
        #if all(isinstance(atom, sympyNumber) 
        #        or isinstance(atom, numbers.Number) 
        #        or isinstance(atom, CountUnit) for atom in comp.atoms()):
        if isinstance(comp, sympyNumber) or isinstance(comp, numbers.Number):
            return float(comp), "inverse"
        # not directly conmparable, not inversely comparable
        raise ValueError("new units are not comparable to existing units")
        
    def units_set(self, varname, unit_repr, replace=False):
        """set units field for given varanem"""
        if not isinstance(varname, str) or not isinstance(unit_repr, str):
            raise TypeError("varname and unit_repr should be str")
        varname = self._find_vars(varname, single=True)[0]
        
        # make sure unit_repr corresponds to known unit
        newUnit = self._get_unit(unit_repr)
            
        # check varDict for existing unit
        chrdict = self._chrdict
        if varname in chrdict:
            if "_units" in chrdict[varname] and not replace:
                msg = "units already set; use -replace- option to replace"
                raise ValueError(msg)
        else:
            chrdict[varname] = {}
        varDict = chrdict[varname]
            
        # set unit 
        varDict["_units"] = unit_repr
        
        self.changed = True
        
    unit_set = units_set
        
    def units_convert(self, varname, unit_repr, delta=None):
        """convert values in existing units to values in unit_repr"""
        global unitsType
        
        if not isinstance(varname, str) or not isinstance(unit_repr, str):
            raise TypeError("varname and unit_repr should be str")
        varname = self._find_vars(varname, single=True)[0]
        
        # make sure unit_repr corresponds to known unit
        newUnit = self._get_unit(unit_repr)
            
        # check varDict for existing unit
        chrdict = self._chrdict
        if varname not in chrdict or "_units" not in chrdict[varname]:
            msg = "need to set units before converting, see method `units_set`"
            raise ValueError(msg)
            
        varDict = chrdict[varname]
        
        # get sympy version of unit
        oldUnit = self._get_unit(varDict["_units"])
        
        # make sure old and new units are comparable (units cancel when divided)
        # function returns factor if comparable, raises error if incomparable
        factor, relType = self._check_comparability(oldUnit, newUnit)
        
        # replace values
        varIndex = self._varlist.index(varname)
        varvals = self._varvals
        if relType == 'direct':
            for row in varvals:
                row[varIndex] *= factor
        else:
            for row in varvals:
                row[varIndex] = 1 / (factor * row[varIndex])
        
        # set unit 
        varDict["_units"] = unit_repr
        
        self.changed = True
        
    unit_convert = units_convert
        
    def units_list(self, varnames = ''):
        varnames = self._find_vars(varnames, evars=False, 
                                   unique=True, empty_ok=True)
        if len(varnames) == 0:
            varnames = self._varlist
               
        chrdict = self._chrdict
        squish_name = self._squish_name
        tplt = "{{res}} {:>20}: {{txt}}{}" if IN_STATA else " {:>20}: {}"
        print("")
        for varname in varnames:
            if varname in chrdict and '_units' in chrdict[varname]:
                squished = squish_name(varname, 20)
                u = chrdict[varname]["_units"]
                print(tplt.format(squished, u))
    
    unit_list = units_list
        
    def units_define(self, name, defn=None, abbrev=None, 
                     ratio=False, count=False, replace=False):
        if not isinstance(name, str):
            raise TypeError("units name must be str")
        if hasattr(units, name) and not replace:
            raise ValueError("unit " + name + " already exists")
        
        if abbrev:
            if not isinstance(abbrev, str):
                raise TypeError("units abbreviation must be str")
            if hasattr(units, abbrev) and not replace:
                raise ValueError("unit " + abbrev + " already exists")
        else:
            abbrev = name
        
        if ratio:
            if count:
                msg = "units are not allowed to be both ratio and count"
                raise ValueError(msg)
            if not defn:
                raise ValueError("must supply definition for units ratio")
            if (not isinstance(defn, tuple) or not len(defn) == 2 or
                    not (isinstance(defn[0], str) and isinstance(defn[1], str))):
                raise ValueError("units ratio should be specified as a 2-element tuple of str")
            setattr(units, name, UnitsRatio(*defn))
        #elif count:
        #    if defn:
        #        raise ValueError("count units are fundamental, do not use definition")
        #    
        #    # set units.name
        #    setattr(units, name, CountUnit(name, abbrev))
        else:
            if defn:
                if not isinstance(defn, str):
                    raise TypeError("units definition must be str")
                # create unit by parsing definition
                setattr(units, name, self._get_unit(defn))
            else:
                setattr(units, name, Unit(name, abbrev))
            
        # set units.abbrev = units.name
        setattr(units, abbrev, getattr(units, name))
        
    unit_define = units_define
        
    def units_discard(self, name):
        if not isinstance(name, str):
            raise TypeError('unit name must be str')
        if not hasattr(units, name):
            raise ValueError('unit ' + name + ' does not exist')
            
        delattr(units, name)
        
    unit_discard = units_discard
    
    def _summ_template(self, w_index=None, w_type=None, detail=False):
        """helper for summarize()"""
        if IN_STATA:
            if detail:
                header = "{{txt}}{}\n{{hline 61}}"
                var_tplt = "".join(
                   ("{{txt}}      Percentiles      Smallest\n",
                    "{{txt}} 1%    {{res}}{:>9g}      {}\n",
                    "{{txt}} 5%    {{res}}{:>9g}      {}\n", 
                    "{{txt}}10%    {{res}}{:>9g}      {}",
                        "       {{txt}}Obs          {{res}}{:>9d}\n",
                    "{{txt}}25%    {{res}}{:>9g}      {}",
                        "       {{txt}}Sum of Wgt.  {{res}}{:>9g}\n",
                    "\n",
                    "{{txt}}50%    {{res}}{:>9g}        ",
                        "              {{txt}}Mean         {{res}}{:>9g}\n",
                    "{{txt}}                        ",
                        "Largest       Std. Dev.    {{res}}{:>9g}\n",
                    "{{txt}}75%    {{res}}{:>9g}      {}\n",
                    "{{txt}}90%    {{res}}{:>9g}      {}",
                        "       {{txt}}Variance     {{res}}{:>9g}\n",
                    "{{txt}}95%    {{res}}{:>9g}      {}",
                        "       {{txt}}Skewness     {{res}}{:>9g}\n",
                    "{{txt}}99%    {{res}}{:>9g}      {}",
                        "       {{txt}}Kurtosis     {{res}}{:>9g}"))
                    
                tplt = (header, var_tplt)
            elif w_index is None or w_type == 'f':
                header = "".join(("\n{txt}    Variable {c |}    Units      ",
                    "Obs       Mean   Std. Dev.      Min       Max"))
                sepline = "{txt}{hline 13}{c +}{hline 60}"
                row = "".join(("{{txt}}{:>12} {{c |}} {:>8} {{res}}{N:>8g} ", 
                               "{mean:>10g} {sd:>10g} {min:>9g} {max:>9g}"))
                zero_row = "{{txt}}{:>12} {{c |}} {:>8} {{res}}       0"
                
                tplt = (header, sepline, row, zero_row)
            else:
                header = "".join(("\n{txt}    Variable {c |}    Units     Obs      ",
                      "Weight        Mean   Std. Dev.       Min        Max"))
                sepline = "{txt}{hline 13}{c +}{hline 68}"
                row = "".join(("{{txt}}{:>12} {{c |}} {:>8} {{res}}",
                               "{N:>6g} {sum_w:>10g} {mean:>10g} ", 
                               "{sd:>9g} {min:>9g} {max:>9g}"))
                zero_row = "{{txt}}{:>12} {{c |}} {:>8} {{res}}     0          0"
                
                tplt = (header, sepline, row, zero_row)
        else:
            if detail:
                header = "".join(("{}\n", "-" * 61))
                var_tplt = "".join(
                   ("      Percentiles      Smallest\n",
                    " 1%    {:>9g}      {}\n",
                    " 5%    {:>9g}      {}\n", 
                    "10%    {:>9g}      {}       Obs          {:>9d}\n",
                    "25%    {:>9g}      {}       Sum of Wgt.  {:>9g}\n",
                    "\n",
                    "50%    {:>9g}", " " * 22, "Mean         {:>9g}\n",
                    " " * 24, "Largest       Std. Dev.    {:>9g}\n",
                    "75%    {:>9g}      {}\n",
                    "90%    {:>9g}      {}       Variance     {:>9g}\n",
                    "95%    {:>9g}      {}       Skewness     {:>9g}\n",
                    "99%    {:>9g}      {}       Kurtosis     {:>9g}"))
                    
                tplt = (header, var_tplt)
            elif w_index is None or w_type == 'f':
                header = "".join(("\n    Variable |    Units      ",
                    "Obs       Mean   Std. Dev.      Min       Max"))
                sepline = "".join(("-" * 13, "+", "-" * 60))
                row = "".join(("{:>12} | {:>8} {N:>8g} {mean:>10g} ", 
                               "{sd:>10g} {min:>9g} {max:>9g}"))
                zero_row = "{:>12} | {:>8}        0"
                
                tplt = (header, sepline, row, zero_row)
            else:
                header = "".join(("\n    Variable |    Units    Obs     ",
                      "Weight       Mean  Std. Dev.      Min       Max"))
                sepline = "".join(("-" * 13, "+", "-" * 68))
                row = "".join(("{:>12} | {:>8} {N:>6g} {sum_w:>10g} {mean:>10g} ", 
                               "{sd:>9g} {min:>9g} {max:>9g}"))
                zero_row = "{:>12} | {:>8}      0          0"
                
                tplt = (header, sepline, row, zero_row)
                            
        return tplt
        
    def _summ_detail(self, wt_index, wt_type, obs, varnames, indexes):
        """do summary if detail"""
        zero_info = {'N': 0, 'sum_w': 0, 'sum': 0, 
                     'key_order': ('N', 'sum_w', 'sum')}
        isnumvar = self._isnumvar
        summ_stats = self._summ_stats_detail
        vlblist = self._vlblist
        chrs = self._chrdict
        
        header, var_tplt = self._summ_template(detail=True)
        print("")
        for i, (name, index) in enumerate(zip(varnames, indexes)):
            if isnumvar(index):
                info, vals = summ_stats(index, wt_index, wt_type, obs)
            else:
                info = zero_info
            
            if name in chrs and '_units' in chrs[name]:
                units = " (" + chrs[name]['_units'] + ")"
            else:
                units = ''
            if len(units) > 18: units = units[:16] + '..'
            label = vlblist[index]
            label = (label[:60 - len(units)] if label != "" else name) + units
            label = "".join((" " * (30 - floor(len(label)/2)), label))
            print(header.format(label))
            if info["N"] != 0:
                print(
                    var_tplt.format(
                        info['p1'], vals[0], 
                        info['p5'], vals[1], 
                        info['p10'], vals[2], info['N'], 
                        info['p25'], vals[3], info['sum_w'], 
                        info['p50'], info['mean'], 
                        info['sd'], 
                        info['p75'], vals[-4], 
                        info['p90'], vals[-3], info['Var'], 
                        info['p95'], vals[-2], info['skewness'], 
                        info['p99'], vals[-1], info['kurtosis']
                    )
                )
            else:
                print("no observations")
           
            print("")
        
        self._return_values = info if info["N"] != 0 else zero_info
    
    def _summ_default(self, wt_index, wt_type, obs, 
                      varnames, indexes, separator):
        """do summary if not detail and not meanonly"""
        zero_info = {'N': 0, 'sum_w': 0, 'sum': 0, 
                     'key_order': ('N', 'sum_w', 'sum')}
        isnumvar = self._isnumvar
        summ_stats = self._summ_stats_default
        squish_name = self._squish_name
        
        chrs = self._chrdict
        
        tplt = self._summ_template(wt_index, wt_type)
        header, sepline, row_tplt, zero_row = tplt
        print(header)
        for i, (name, index) in enumerate(zip(varnames, indexes)):
            if i % separator == 0: print(sepline)
            
            if isnumvar(index):
                info = summ_stats(index, wt_index, wt_type, obs)
            else:
                info = zero_info
            
            small_name = squish_name(name, 12)
            
            if name in chrs and '_units' in chrs[name]:
                units = chrs[name]['_units']
            else:
                units = ''
                
            if len(units) > 8: units = units[:6] + '..'
            
            if info["N"] != 0:
                print(row_tplt.format(small_name, units, **info))
            else:
                print(zero_row.format(small_name, units))
        
        print("")
        self._return_values = info if info["N"] != 0 else zero_info
