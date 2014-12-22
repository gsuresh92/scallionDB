''' 
  Licensed under the Apache License, Version 2.0 (the "License"); you may
  not use this file except in compliance with the License. You may obtain
  a copy of the License at
 
      http://www.apache.org/licenses/LICENSE-2.0
 
  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
 '''
 
import json
from zclient import send_request
from constants import *

class Tree(object):

    def __init__(self,name,request):
        self.name = name
        self.request = request
        
    def getTree(self,selector,reference="SELF"):
        if reference.upper() not in tree_references:
            raise SyntaxError("Error: GETTREE - Invalid reference type."
             			      "Valid references are %s" %str(tree_references))
        if isinstance(selector,dict):
            try:
                selector = json.dumps(selector)
            except:
                raise SyntaxError("Error: GETTREE - Invalid JSON")
        elif isinstance(selector,list):
            if not all([isinstance(a,dict) for a in selector]):
                raise SyntaxError("All elements in selector should be dict type")          
            try:
                selector = json.dumps(selector)
            except:
                raise SyntaxError("Error: GETTREE - Invalid JSON")		
        else:
            raise SyntaxError("Error: GETTREE - Selector is not of type dict or list")
        
        statement = ' '.join(["GET","TREE",str(self.name),
		                      reference.upper(),selector])					
        return send_request(self.request, statement)
    
    def getAttrs(self,selector,attribute_list='*',reference='SELF'):
        if reference.upper() not in references:
            raise SyntaxError("Error: GETATTR - Invalid reference type."
             			      "Valid references are %s" %str(references))

        if isinstance(selector,dict):
            try:
                selector = json.dumps(selector)
            except:
                raise SyntaxError("Error: GETATTR - Invalid JSON")
        elif isinstance(selector,list):
            if not all([isinstance(a,dict) for a in selector]):
                raise SyntaxError("All elements in selector should be dict type")          
            try:
                selector = json.dumps(selector)
            except:
                raise SyntaxError("Error: GETATTR - Invalid JSON")		
        else:
            raise SyntaxError("Error: GETATTR - Selector is not of type dict or list")

        if not(isinstance(attribute_list,list) or attribute_list == '*'):
            raise SyntaxError("Error: GETATTR - attribute_list should be" 
			                   " a list of attributes (or * for all attributes)")
        if isinstance(attribute_list,list):
            if "_children" in attribute_list:
                raise Exception("Error: GETATTR - _children isn't a valid attribute")
            if not all([isinstance(each,basestring) for each in attribute_list]):
                raise SyntaxError("Error: GETATTR - Invalid list of attributes!"
               			     	  "Each attribute should be of string type")
            attribute_list = json.dumps(attribute_list)

        statement = ' '.join(["GET","ATTR",str(self.name),reference.upper(),
		                   selector,attribute_list])						
        return send_request(self.request, statement)
        
    def putTree(self,selector,tree,reference='SELF'):

        if reference.upper() not in tree_references:
            raise SyntaxError("Error: PUTTREE - Invalid reference type."
             			      "Valid references are %s" %str(tree_references))
							  
        if isinstance(selector,dict):
            try:
                selector = json.dumps(selector)
            except:
                raise SyntaxError("Error: PUTTREE - Invalid JSON")
        elif isinstance(selector,list):
            if not all([isinstance(a,dict) for a in selector]):
                raise SyntaxError("All elements in selector should be dict type")          
            try:
                selector = json.dumps(selector)
            except:
                raise SyntaxError("Error: PUTTREE - Invalid JSON")		
        else:
            raise SyntaxError("Error: PUTTREE - Selector is not of type dict or list")
			
        if isinstance(tree,dict):
            try:
                tree = json.dumps(tree)
            except:
                raise SyntaxError("Error: PUTTREE - INVALID New Tree JSON!!")
        else:
            raise SyntaxError("Error: PUTTREE - Tree should be of dict type")
        statement = ' '.join(["PUT","TREE",self.name,reference.upper(),
		                       selector,tree])  							
        return send_request(self.request, statement)
        
    def putAttrs(self,selector,attr_dict,reference='SELF'):
        if reference.upper() not in references:
            raise SyntaxError("Error: PUTATTR - Invalid reference type."
             			      "Valid references are %s" %str(references))

        if isinstance(selector,dict):
            try:
                selector = json.dumps(selector)
            except:
                raise SyntaxError("Error: PUTATTR - Invalid JSON")
        elif isinstance(selector,list):
            if not all([isinstance(a,dict) for a in selector]):
                raise SyntaxError("All elements in selector should be dict type")          
            try:
                selector = json.dumps(selector)
            except:
                raise SyntaxError("Error: PUTATTR - Invalid JSON")		
        else:
            raise SyntaxError("Error: PUTATTR - Selector is not of type dict or list")
			

        if isinstance(attr_dict,dict):
            if "_id" in attr_dict.keys() or "_children" in attr_dict.keys():
                raise Exception("Error: PUTATTR - _id & _children aren't"
                				" attrs types that can be put")
            try:
                attr_dict = json.dumps(attr_dict)
            except:
                raise SyntaxError("Error: PUTATTR - INVALID attrdict JSON!")
        else:
            raise SyntaxError("Error: PUTATTR - attrdict should be of dict type")

            
        statement = ' '.join(["PUT","ATTR",self.name,reference.upper(),
		                      selector,attr_dict])							
        return send_request(self.request, statement)   
		
    def delTree(self,selector,reference="SELF"):
        if reference.upper() not in tree_references:
            raise SyntaxError("Error: DELTREE - Invalid reference type."
             			      "Valid references are %s" %str(tree_references))
							  
        if isinstance(selector,dict):
            try:
                selector = json.dumps(selector)
            except:
                raise SyntaxError("Error: DELTREE - Invalid JSON")
        elif isinstance(selector,list):
            if not all([isinstance(a,dict) for a in selector]):
                raise SyntaxError("All elements in selector should be dict type")          
            try:
                selector = json.dumps(selector)
            except:
                raise SyntaxError("Error: DELTREE - Invalid JSON")		
        else:
            raise SyntaxError("Error: DELTREE - Selector is not of type dict or list")
			
        statement = ' '.join(["DELETE","TREE",self.name,
		                      reference.upper(),selector])
							  	
        return send_request(self.request, statement)   
    
    def delAttrs(self,selector,attribute_list='*',reference="SELF"):

        if reference.upper() not in references:
            raise SyntaxError("Error: DELATTR - Invalid reference type."
             			      "Valid references are %s" %str(references))
							  
        if isinstance(selector,dict):
            try:
                selector = json.dumps(selector)
            except:
                raise SyntaxError("Error: DELATTR - Invalid JSON")
        elif isinstance(selector,list):
            if not all([isinstance(a,dict) for a in selector]):
                raise SyntaxError("All elements in selector should be dict type")          
            try:
                selector = json.dumps(selector)
            except:
                raise SyntaxError("Error: DELATTR - Invalid JSON")		
        else:
            raise SyntaxError("Error: DELATTR - Selector is not of type dict or list")
			
        if not(isinstance(attribute_list,list) or attribute_list == '*'):
            raise SyntaxError("Error: DELATTR - attribute_list should be" 
			                   " a list of attributes (or * for all attributes)")
        if isinstance(attribute_list,list):
            if "_children" in attribute_list:
                raise Exception("Error: DELATTR - _children isn't a valid attribute")
            if "_id" in attribute_list:
                raise Exception("Error: DELATTR - _id isn't a valid attribute")
            if not all([isinstance(each,basestring) for each in attribute_list]):
                raise SyntaxError("Error: DELATTR - Invalid list of attributes!"
               			     	  "Each attribute should be of string type")
            attribute_list = json.dumps(attribute_list)

        statement = ' '.join(["DELETE","ATTR",self.name,reference.upper(),
		                      selector,attribute_list])
							
        return send_request(self.request, statement)    
		
    def loadTree(self,path):

        statement = ' '.join(["LOAD",self.name,path])						
        return send_request(self.request, statement)   
		
    def saveTree(self):
        statement = ' '.join(["SAVE", self.name])
        return send_request(self.request, statement)
    
    def descTree(self):
        raise Exception("Need to think about what this will do")

        
