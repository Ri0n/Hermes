import os
from ply import lex, yacc
from rcore import config

# grammar
# list > <list>,<element>
# list > <element>
# element > <servicerule>
# element > <tagrule>
# servicerule > @d[<taglist>]
# taglist > <taglist>,<tagrule>
# taglist > <tagrule>
# tagrule > t
# tagrule > ^t
# tagrule > *
#

# ^*,@serv1[*,^notice] - disable all, enable all for serv1 except notice

# tokens
# t - word[a-z]
# , - separator
# [ - start of tags list
# ] - end of tags list
# ^ - ignore next up to separator
# @ - select service
# * - any tag
#


class Service(object):
    def __init__(self, name="__default__"):
        self.name = name
        self.tags = set()
        self.ignoredTags = set()
        self.enableAll = False
        self.disableAll = False
        
    def __str__(self):
        enable = ",".join(self.tags)
        disable = ",".join(["^" + item for item in self.ignoredTags])
        if self.enableAll:
            tags = "*," + disable
        elif self.disableAll:
            tags = "^*," + enable
        else:
            tags = ",".join([enable,disable])
        tags = tags.strip(",")
        if self.name == "__default__":
            return tags
        else:
            return "@%s[%s]" % (self.name, tags) if len(tags) else ""
        
    def addTagTuple(self, t):
        if t[1]:
            self.enableTag(t[0])
        else:
            self.disableTag(t[0])

        
    def enableTag(self, name):
        if name == '*':
            self.enableAll = True
            self.disableAll = False
        else:
            if name in self.ignoredTags: self.ignoredTags.remove(name)
            self.tags.add(name)
        
    def disableTag(self, name):
        if name == '*':
            self.enableAll = False
            self.disableAll = True
        else:
            self.ignoredTags.add(name)
            if name in self.tags: self.tags.remove(name)
            
    def optimizeAgainstDefault(self, d):
        if d.enableAll:
            self.tags = set()
            self.enableAll = False
        elif d.disableAll:
            self.ignoredTags = set()
            self.disableAll = False
        return len(self.tags) or len(self.ignoredTags) or self.enableAll or self.disableAll
    
    def match(self, tags):
        if tags & self.tags:
            return True
        if tags & self.ignoredTags:
            return False
        if self.enableAll:
            return True
        if self.disableAll:
            return False
        return None
        
        

class TagParser:

    tokens = (
       'TAG',
       'SERVICE'
    )
    
    literals = "^[],*"
    
    t_TAG = r'[a-zA-Z][a-zA-Z0-9]*'
    t_ignore  = ' \t'
    
    
    
    # Build the lexer
    def __init__(self,**kwargs):
        self.lexer = lex.lex(module=self, **kwargs)
        self.parser = yacc.yacc(module=self,
                                outputdir=config().spool.path,
                                debugfile=os.path.join(config().spool.path, "tag_parser_debug.log"))
        
    
    def t_SERVICE(self, t):
        r'\@[a-zA-Z][a-zA-Z0-9]*'
        name = t.value[1:]
        if name not in self.services:
            self.services[name] = Service(name)
        t.value = self.services[name]
        return t
    
    # Error handling rule
    def t_error(self, t):
        print "Illegal character '%s'" % t.value[0]
        t.lexer.skip(1)
        
    def p_list(self, p):
        "list : list ',' element"
        p[0] = p[1][:]
        p[0].append(p[3])
        
    def p_list_single(self, p):
        "list : element"
        p[0] = [p[1]]
        
    def p_element(self, p):
        """element : servicerule
                   | tagrule"""
        if not isinstance(p[1], Service): # tag
            self.defaultService.addTagTuple(p[1])
        p[0] = p[1]
        
    def p_servicerule(self, p):
        "servicerule : SERVICE '[' taglist ']'"
        for t in p[3]:
            p[1].addTagTuple(t)
        p[0] = p[1]
        
    def p_tagrule(self, p):
        """tagrule : TAG
                   | '^' TAG
                   | '*'
                   | '^' '*'"""
        enable = True
        if p[1] == '^':
            enable = False
            tag = p[2]
        else:
            tag = p[1]
        p[0] = (tag, enable)
        
    def p_taglist_single(self, p):
        """taglist : tagrule"""
        p[0] = [p[1]]
        
    def p_taglist_list(self, p):
        """taglist : taglist ',' tagrule"""
        p[0] = p[1][:]
        p[0].append(p[3])
        
    def servicesFromString(self, data):
        self.services = dict()
        self.defaultService = Service()
        self.defaultService.disableAll = True # we need this default rule
        self.services["__default__"] = self.defaultService
        self.parser.parse(data)
        for k,r in self.services.items():
            if r != self.defaultService:
                if not r.optimizeAgainstDefault(self.defaultService): # optimized out
                    del self.services[k]
        return self.services

    def parse(self, data):
        print ",".join([str(s) for s in self.servicesFromString(data).values()]).strip(",")

if __name__ == "__main__":
    tp = TagParser()
    tp.parse("*,@serv1[error,^notice],error,@serv2[*],@serv1[^warning]")
