#!/usr/bin/env python
"""
Template Documentation Generator
Generates minified documentation for Django templates to reduce AI context size
"""
import os
import re
from pathlib import Path
import json
from typing import Dict, List, Set, Tuple

class TemplateDocGenerator:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.template_docs = {}
        
    def generate_all_docs(self):
        """Generate documentation for all templates in the project"""
        # Find all template directories
        template_dirs = []
        for root, dirs, files in os.walk(self.project_root):
            if 'templates' in dirs:
                template_dirs.append(Path(root) / 'templates')
        
        # Process each template
        for template_dir in template_dirs:
            for template_path in template_dir.rglob('*.html'):
                self.generate_template_doc(template_path)
        
        # Generate manifest file
        self.generate_manifest()
        
        # Generate individual summary files
        self.generate_summary_files()
    
    def generate_template_doc(self, template_path: Path) -> Dict:
        """Generate documentation for a single template"""
        relative_path = template_path.relative_to(self.project_root)
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doc = {
            'path': str(relative_path),
            'extends': self.extract_extends(content),
            'blocks': self.extract_blocks(content),
            'includes': self.extract_includes(content),
            'urls': self.extract_urls(content),
            'context_vars': self.extract_context_vars(content),
            'forms': self.extract_forms(content),
            'static_files': self.extract_static_files(content),
            'js_functions': self.extract_js_functions(content),
            'css_classes': self.extract_css_classes(content),
            'purpose': self.extract_purpose(content, relative_path),
            'ajax_endpoints': self.extract_ajax_endpoints(content)
        }
        
        self.template_docs[str(relative_path)] = doc
        return doc
    
    def extract_extends(self, content: str) -> str:
        """Extract template inheritance"""
        match = re.search(r'{%\s*extends\s+["\']([^"\']+)["\']', content)
        return match.group(1) if match else None
    
    def extract_blocks(self, content: str) -> List[str]:
        """Extract block names"""
        blocks = re.findall(r'{%\s*block\s+(\w+)', content)
        return list(set(blocks))
    
    def extract_includes(self, content: str) -> List[str]:
        """Extract included templates"""
        includes = re.findall(r'{%\s*include\s+["\']([^"\']+)["\']', content)
        return list(set(includes))
    
    def extract_urls(self, content: str) -> List[Dict[str, str]]:
        """Extract URL reversals"""
        urls = []
        # Standard URL tags
        url_matches = re.findall(r'{%\s*url\s+["\']([^"\']+)["\']([^%}]*)', content)
        for url_name, params in url_matches:
            urls.append({
                'name': url_name,
                'params': params.strip() if params else None
            })
        
        # Form actions
        action_matches = re.findall(r'action="{% url ["\']([^"\']+)["\']', content)
        for url_name in action_matches:
            urls.append({'name': url_name, 'type': 'form_action'})
        
        return urls
    
    def extract_context_vars(self, content: str) -> List[str]:
        """Extract Django template variables"""
        # Remove script and style content first
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        
        # Find all template variables
        vars_pattern = r'{{\s*([^}|]+)'
        matches = re.findall(vars_pattern, content)
        
        context_vars = set()
        for match in matches:
            # Extract the base variable name
            var_name = match.strip().split('.')[0].split('[')[0]
            if var_name and not var_name.startswith(('form.', 'field.')):
                context_vars.add(var_name)
        
        return sorted(list(context_vars))
    
    def extract_forms(self, content: str) -> List[Dict[str, any]]:
        """Extract form information"""
        forms = []
        
        # Find form tags with their attributes
        form_matches = re.finditer(
            r'<form[^>]*method=["\'](\w+)["\'][^>]*>(.*?)</form>',
            content,
            re.DOTALL
        )
        
        for match in form_matches:
            method = match.group(1)
            form_content = match.group(2)
            
            # Extract form fields
            fields = re.findall(r'{{\s*(\w+_form\.\w+)', form_content)
            fields.extend(re.findall(r'name=["\'](\w+)["\']', form_content))
            
            # Extract action URL
            action_match = re.search(r'action="{% url ["\']([^"\']+)["\']', match.group(0))
            
            forms.append({
                'method': method,
                'action': action_match.group(1) if action_match else 'current_url',
                'fields': list(set(fields))
            })
        
        return forms
    
    def extract_static_files(self, content: str) -> Dict[str, List[str]]:
        """Extract static file references"""
        return {
            'css': re.findall(r'href="[^"]*\.css[^"]*"', content),
            'js': re.findall(r'src="[^"]*\.js[^"]*"', content),
            'images': re.findall(r'src="[^"]*\.(png|jpg|jpeg|gif|svg)[^"]*"', content)
        }
    
    def extract_js_functions(self, content: str) -> List[Dict[str, str]]:
        """Extract JavaScript function definitions"""
        functions = []
        
        # Find script blocks
        script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
        
        for script in script_blocks:
            # Function declarations
            func_matches = re.findall(r'function\s+(\w+)\s*\([^)]*\)', script)
            for func_name in func_matches:
                functions.append({'name': func_name, 'type': 'declaration'})
            
            # Object methods
            method_matches = re.findall(r'(\w+)\s*:\s*function\s*\([^)]*\)', script)
            for method_name in method_matches:
                functions.append({'name': method_name, 'type': 'method'})
            
            # Arrow functions assigned to variables
            arrow_matches = re.findall(r'(?:const|let|var)\s+(\w+)\s*=\s*\([^)]*\)\s*=>', script)
            for func_name in arrow_matches:
                functions.append({'name': func_name, 'type': 'arrow'})
        
        return functions
    
    def extract_css_classes(self, content: str) -> Dict[str, List[str]]:
        """Extract custom CSS classes defined in the template"""
        classes = {
            'custom': [],
            'bootstrap': [],
            'ids': []
        }
        
        # Find style blocks
        style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)
        
        for style in style_blocks:
            # Custom classes
            custom_classes = re.findall(r'\.([a-zA-Z][\w-]*)\s*{', style)
            classes['custom'].extend(custom_classes)
            
            # IDs
            ids = re.findall(r'#([a-zA-Z][\w-]*)\s*{', style)
            classes['ids'].extend(ids)
        
        # Bootstrap classes used (common ones)
        bootstrap_patterns = [
            r'class="[^"]*\b(btn-\w+)',
            r'class="[^"]*\b(col-\w+-\d+)',
            r'class="[^"]*\b(text-\w+)',
            r'class="[^"]*\b(bg-\w+)',
        ]
        
        for pattern in bootstrap_patterns:
            classes['bootstrap'].extend(re.findall(pattern, content))
        
        # Deduplicate
        for key in classes:
            classes[key] = sorted(list(set(classes[key])))
        
        return classes
    
    def extract_purpose(self, content: str, path: Path) -> str:
        """Infer template purpose from path and content"""
        path_str = str(path).lower()
        
        if 'list' in path_str:
            return "List/index view for displaying multiple items"
        elif 'detail' in path_str:
            return "Detail view for displaying single item"
        elif 'create' in path_str:
            return "Create/add new item form"
        elif 'update' in path_str or 'edit' in path_str:
            return "Update/edit existing item form"
        elif 'dashboard' in path_str:
            return "Dashboard view with summary information"
        elif 'login' in path_str:
            return "User authentication login page"
        elif 'base' in path_str:
            return "Base template for inheritance"
        elif 'timesheet' in path_str:
            return "Time tracking and timesheet display"
        elif 'roster' in path_str:
            return "Roster/schedule display"
        else:
            # Try to infer from content
            if re.search(r'<form.*method="post"', content, re.IGNORECASE):
                return "Form submission page"
            elif re.search(r'{% for .* in .* %}', content):
                return "List/iteration display page"
            else:
                return "Display/information page"
    
    def extract_ajax_endpoints(self, content: str) -> List[Dict[str, str]]:
        """Extract AJAX endpoints from JavaScript"""
        endpoints = []
        
        # Find fetch() calls
        fetch_matches = re.findall(r'fetch\(["\']([^"\']+)["\']', content)
        for endpoint in fetch_matches:
            endpoints.append({'url': endpoint, 'type': 'fetch'})
        
        # Find jQuery AJAX calls
        ajax_matches = re.findall(r'\$\.(?:ajax|get|post)\(["\']([^"\']+)["\']', content)
        for endpoint in ajax_matches:
            endpoints.append({'url': endpoint, 'type': 'jquery'})
        
        return endpoints
    
    def generate_manifest(self):
        """Generate a manifest file with all template relationships"""
        manifest = {
            'total_templates': len(self.template_docs),
            'inheritance_tree': self.build_inheritance_tree(),
            'url_mapping': self.build_url_mapping(),
            'template_groups': self.group_templates(),
            'context_var_index': self.build_context_var_index()
        }
        
        manifest_path = self.project_root / 'docs' / 'template_manifest.json'
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
    
    def build_inheritance_tree(self) -> Dict:
        """Build template inheritance tree"""
        tree = {}
        
        for path, doc in self.template_docs.items():
            if doc['extends']:
                parent = doc['extends']
                if parent not in tree:
                    tree[parent] = []
                tree[parent].append(path)
        
        return tree
    
    def build_url_mapping(self) -> Dict[str, List[str]]:
        """Map URL names to templates that use them"""
        url_map = {}
        
        for path, doc in self.template_docs.items():
            for url in doc['urls']:
                url_name = url['name']
                if url_name not in url_map:
                    url_map[url_name] = []
                url_map[url_name].append(path)
        
        return url_map
    
    def group_templates(self) -> Dict[str, List[str]]:
        """Group templates by app and type"""
        groups = {}
        
        for path in self.template_docs.keys():
            parts = path.split('/')
            if 'templates' in parts:
                idx = parts.index('templates')
                if idx > 0:
                    app = parts[idx - 1]
                    if app not in groups:
                        groups[app] = []
                    groups[app].append(path)
        
        return groups
    
    def build_context_var_index(self) -> Dict[str, List[str]]:
        """Index templates by context variables used"""
        var_index = {}
        
        for path, doc in self.template_docs.items():
            for var in doc['context_vars']:
                if var not in var_index:
                    var_index[var] = []
                var_index[var].append(path)
        
        return var_index
    
    def generate_summary_files(self):
        """Generate individual summary files for each template"""
        summary_dir = self.project_root / 'docs' / 'template_summaries'
        summary_dir.mkdir(parents=True, exist_ok=True)
        
        for path, doc in self.template_docs.items():
            summary = self.create_summary(path, doc)
            
            # Create summary file path - handle Windows paths
            safe_filename = path.replace('/', '_').replace('\\', '_').replace('.html', '.md')
            summary_path = summary_dir / safe_filename
            
            # Ensure the parent directory exists
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(summary)
    
    def create_summary(self, path: str, doc: Dict) -> str:
        """Create a markdown summary for a template"""
        summary = f"""# Template: {path}

## Purpose
{doc['purpose']}

## Template Inheritance
- **Extends:** {doc['extends'] or 'None (base template)'}
- **Blocks:** {', '.join(doc['blocks']) if doc['blocks'] else 'None'}

## Dependencies
- **Includes:** {', '.join(doc['includes']) if doc['includes'] else 'None'}
- **URLs Used:** {', '.join([u['name'] for u in doc['urls']]) if doc['urls'] else 'None'}

## Context Variables Required
```python
context = {{
"""
        for var in doc['context_vars']:
            summary += f"    '{var}': ...,  # Required\n"
        
        summary += """}}
```

## Forms
"""
        if doc['forms']:
            for form in doc['forms']:
                summary += f"- **{form['method'].upper()} to {form['action']}**\n"
                if form['fields']:
                    summary += f"  - Fields: {', '.join(form['fields'][:5])}{'...' if len(form['fields']) > 5 else ''}\n"
        else:
            summary += "No forms in this template.\n"
        
        summary += "\n## JavaScript Functions\n"
        if doc['js_functions']:
            for func in doc['js_functions'][:10]:  # Limit to first 10
                summary += f"- `{func['name']}()` ({func['type']})\n"
            if len(doc['js_functions']) > 10:
                summary += f"- ... and {len(doc['js_functions']) - 10} more\n"
        else:
            summary += "No JavaScript functions defined.\n"
        
        summary += "\n## Custom CSS Classes\n"
        if doc['css_classes']['custom']:
            summary += f"- Custom: {', '.join(doc['css_classes']['custom'][:10])}"
            if len(doc['css_classes']['custom']) > 10:
                summary += f" ... and {len(doc['css_classes']['custom']) - 10} more"
            summary += "\n"
        
        if doc['ajax_endpoints']:
            summary += "\n## AJAX Endpoints\n"
            for endpoint in doc['ajax_endpoints']:
                summary += f"- {endpoint['url']} ({endpoint['type']})\n"
        
        return summary


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python generate_template_docs.py <project_root>")
        sys.exit(1)
    
    project_root = sys.argv[1]
    generator = TemplateDocGenerator(project_root)
    generator.generate_all_docs()
    
    print(f"Generated documentation for {len(generator.template_docs)} templates")
    print(f"Check the 'docs' directory for the generated files")