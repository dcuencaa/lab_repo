import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
from urllib.parse import urlparse
import dns.resolver
import re
import subprocess
import socket
import tempfile
import os
import shutil

class AkaCurlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Aka Curl - Akamai Edge Testing Tool")
        self.root.geometry("850x950") # Slightly taller to accommodate the larger text boxes

        # --- Apply UX/UI Styling: "Cove" Palette ---
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")

        # Cove Palette Hex Codes
        self.bg_cream = "#FFE3B3"
        self.fg_dark_blue = "#006BBB"
        self.btn_light_blue = "#30A0E0"
        self.accent_orange = "#FFC872"

        # Configure Custom Styles using the palette
        self.style.configure("Cove.TLabelframe", background=self.bg_cream, borderwidth=2, bordercolor=self.btn_light_blue)
        self.style.configure("Cove.TLabelframe.Label", background=self.bg_cream, font=("Helvetica", 11, "bold"), foreground=self.fg_dark_blue)
        
        self.style.configure("Cove.TLabel", background=self.bg_cream, font=("Helvetica", 10, "bold"), foreground=self.fg_dark_blue)
        self.style.configure("Cove.TCheckbutton", background=self.bg_cream, font=("Helvetica", 10, "bold"), foreground=self.fg_dark_blue)
        self.style.configure("Cove.TFrame", background=self.bg_cream)

        # Primary Action Button Style
        self.style.configure("Accent.TButton", font=("Helvetica", 10, "bold"), background=self.btn_light_blue, foreground="white")
        self.style.map("Accent.TButton", background=[("active", self.fg_dark_blue)])

        self.create_widgets()

        # Keyboard Bindings for Search (Using bind_all so Text widgets don't intercept it)
        self.root.bind_all("<Control-f>", self.toggle_search_bar)
        self.root.bind_all("<Command-f>", self.toggle_search_bar) # For macOS

    def create_widgets(self):
        # --- Top Frame: Input Parameters (Cove Cream Area) ---
        input_frame = ttk.LabelFrame(self.root, text=" Request Settings ", padding=15, style="Cove.TLabelframe")
        input_frame.pack(fill=tk.X, padx=15, pady=10)

        # Custom Text Widget styling for a cleaner look
        text_kwargs = {"font": ("Courier", 10), "relief": "flat", "highlightthickness": 1, "highlightcolor": self.btn_light_blue, "highlightbackground": "#CCCCCC"}

        # Row 0: URL Input (Height: 8)
        ttk.Label(input_frame, text="Provide URL:", style="Cove.TLabel").grid(row=0, column=0, sticky=tk.NW, pady=4)
        self.url_entry = tk.Text(input_frame, height=8, width=70, **text_kwargs)
        self.url_entry.grid(row=0, column=1, columnspan=3, sticky=tk.W, pady=4)
        self.url_entry.insert("1.0", "https://www.example.com")

        # Row 1: Edge IP / Hostname Input
        ttk.Label(input_frame, text="Spoof IP / Hostname:", style="Cove.TLabel").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.edge_ip_entry = ttk.Entry(input_frame, width=30, font=("Helvetica", 10))
        self.edge_ip_entry.grid(row=1, column=1, sticky=tk.W, pady=4)
        ttk.Label(input_frame, text="(Optional: Leave blank for auto CNAME/Map)", style="Cove.TLabel", foreground="#888888").grid(row=1, column=2, sticky=tk.W, pady=4)

        # Row 2: Target Network
        ttk.Label(input_frame, text="Network & Env:", style="Cove.TLabel").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.network_var = tk.StringVar(value="Std TLS (staging)")
        networks = [
            "Std TLS (production)", 
            "Std TLS (staging)", 
            "Enhanced TLS (production)", 
            "Enhanced TLS (staging)"
        ]
        ttk.Combobox(input_frame, textvariable=self.network_var, values=networks, width=25, state="readonly").grid(row=2, column=1, sticky=tk.W)

        # Row 3: HTTP Method & HTTP Version
        ttk.Label(input_frame, text="Method & HTTP:", style="Cove.TLabel").grid(row=3, column=0, sticky=tk.W, pady=4)
        
        frame_method_http = ttk.Frame(input_frame, style="Cove.TFrame")
        frame_method_http.grid(row=3, column=1, columnspan=2, sticky=tk.W)
        
        self.method_var = tk.StringVar(value="GET")
        ttk.Combobox(frame_method_http, textvariable=self.method_var, values=["GET", "POST", "PUT", "HEAD"], width=8, state="readonly").pack(side=tk.LEFT)
        
        ttk.Label(frame_method_http, text="   Version: ", style="Cove.TLabel").pack(side=tk.LEFT)
        self.http_var = tk.StringVar(value="HTTP/1.1")
        ttk.Combobox(frame_method_http, textvariable=self.http_var, values=["HTTP/1.1", "HTTP/2", "HTTP/3"], width=10, state="readonly").pack(side=tk.LEFT)

        # Row 4: Toggles (Pragma, Show Body, Ignore Certs)
        self.pragma_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(input_frame, text="Pragma Headers", variable=self.pragma_var, style="Cove.TCheckbutton").grid(row=4, column=0, sticky=tk.W, pady=8)

        self.show_body_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(input_frame, text="Save/Show Body", variable=self.show_body_var, style="Cove.TCheckbutton").grid(row=4, column=1, sticky=tk.W, pady=8)

        self.ignore_cert_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(input_frame, text="Ignore Cert Errors (-k)", variable=self.ignore_cert_var, style="Cove.TCheckbutton").grid(row=4, column=2, columnspan=2, sticky=tk.W, pady=8)

        # Row 5: Custom Headers (Height: 6)
        ttk.Label(input_frame, text="Custom Headers:\n(Comma or newline)", style="Cove.TLabel").grid(row=5, column=0, sticky=tk.NW, pady=4)
        self.headers_text = tk.Text(input_frame, height=6, width=70, **text_kwargs)
        self.headers_text.grid(row=5, column=1, columnspan=3, pady=4)
        #self.headers_text.insert("1.0", "Accept-Encoding: gzip\n")

        # Row 6: Payload Input (Height: 6)
        ttk.Label(input_frame, text="Payload:\n(POST/PUT)", style="Cove.TLabel").grid(row=6, column=0, sticky=tk.NW, pady=4)
        self.payload_text = tk.Text(input_frame, height=6, width=70, **text_kwargs)
        self.payload_text.grid(row=6, column=1, columnspan=3, pady=4)

        # Row 7: Submit Button
        submit_btn = ttk.Button(input_frame, text="  Send Request  ", command=self.send_request, style="Accent.TButton")
        submit_btn.grid(row=7, column=1, pady=15, sticky=tk.W)

        # --- Bottom Frame: Output with Tabs ---
        output_frame = ttk.Frame(self.root, padding=15)
        output_frame.pack(fill=tk.BOTH, expand=True)

        self.target_label = ttk.Label(output_frame, text="Routed to: N/A", font=("Helvetica", 9, "italic"), foreground="#555555")
        self.target_label.pack(anchor=tk.W, pady=(0, 5))

        self.config_label = ttk.Label(output_frame, text="Config / CP Code: N/A", font=("Helvetica", 11, "bold"), foreground=self.fg_dark_blue)
        self.config_label.pack(anchor=tk.W, pady=(0, 10))

        # Notebook (Tabs)
        self.notebook = ttk.Notebook(output_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab configuration
        tab_kwargs = {"wrap": tk.WORD, "font": ("Courier", 10), "relief": "flat", "highlightthickness": 0}

        # Tab 1: Headers
        self.tab_headers = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_headers, text=" Response Headers ")
        self.response_text = scrolledtext.ScrolledText(self.tab_headers, **tab_kwargs)
        self.response_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Tab 2: Body
        self.tab_body = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_body, text=" Response Body ")
        self.body_text = scrolledtext.ScrolledText(self.tab_body, **tab_kwargs)
        self.body_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Tab 3: Raw Certificate Details
        self.tab_cert = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_cert, text=" Raw Cert / SSL ")
        self.cert_text = scrolledtext.ScrolledText(self.tab_cert, **tab_kwargs)
        self.cert_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Tab 4: Decoded Certificate
        self.tab_cert_decoded = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_cert_decoded, text=" Decoded Cert ")
        self.cert_decoded_text = scrolledtext.ScrolledText(self.tab_cert_decoded, **tab_kwargs)
        self.cert_decoded_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Tab 5: CURL
        self.tab_curl = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_curl, text=" CURL & Debug ")
        self.curl_text = scrolledtext.ScrolledText(self.tab_curl, **tab_kwargs)
        self.curl_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Mapping tabs to their respective text widgets for search capability
        self.tab_text_map = {
            str(self.tab_headers): self.response_text,
            str(self.tab_body): self.body_text,
            str(self.tab_cert): self.cert_text,
            str(self.tab_cert_decoded): self.cert_decoded_text,
            str(self.tab_curl): self.curl_text
        }

        # --- Search Bar Frame (Hidden by Default) ---
        self.search_frame = ttk.Frame(output_frame)

        ttk.Label(self.search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.perform_search)
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind("<Return>", self.find_next)
        self.search_entry.bind("<Escape>", self.close_search_bar)
        
        ttk.Button(self.search_frame, text="Next", command=self.find_next, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.search_frame, text="Close", command=self.close_search_bar, width=6).pack(side=tk.LEFT, padx=2)

        self.search_match_positions = []
        self.current_match_index = -1

    def toggle_search_bar(self, event=None):
        if not self.search_frame.winfo_ismapped():
            # FIXED: Added `before=self.notebook` to prevent the search bar from being crushed to 0 height
            self.search_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0), before=self.notebook)
            self.search_entry.focus_set()
        else:
            self.search_entry.focus_set()
            self.search_entry.selection_range(0, tk.END)
        return "break" # Prevents default Text widget behaviors from overriding the global shortcut

    def close_search_bar(self, event=None):
        self.search_frame.pack_forget()
        self.clear_search_highlights()
        return "break"

    def get_current_text_widget(self):
        current_tab_id = self.notebook.select()
        return self.tab_text_map.get(current_tab_id)

    def clear_search_highlights(self):
        text_widget = self.get_current_text_widget()
        if text_widget:
            text_widget.tag_remove('search', '1.0', tk.END)
            text_widget.tag_remove('search_active', '1.0', tk.END)

    def perform_search(self, *args):
        text_widget = self.get_current_text_widget()
        if not text_widget:
            return

        self.clear_search_highlights()
        self.search_match_positions = []
        self.current_match_index = -1

        query = self.search_var.get()
        if not query:
            return

        start_pos = '1.0'
        while True:
            start_pos = text_widget.search(query, start_pos, stopindex=tk.END, nocase=True)
            if not start_pos:
                break
            
            end_pos = f"{start_pos}+{len(query)}c"
            text_widget.tag_add('search', start_pos, end_pos)
            self.search_match_positions.append((start_pos, end_pos))
            start_pos = end_pos

        text_widget.tag_config('search', background='yellow', foreground='black')
        
        if self.search_match_positions:
            self.find_next()

    def find_next(self, event=None):
        if not self.search_match_positions:
            return

        text_widget = self.get_current_text_widget()
        if not text_widget:
            return

        self.current_match_index = (self.current_match_index + 1) % len(self.search_match_positions)
        match_start, match_end = self.search_match_positions[self.current_match_index]

        text_widget.tag_remove('search_active', '1.0', tk.END)
        text_widget.tag_add('search_active', match_start, match_end)
        text_widget.tag_config('search_active', background='orange', foreground='black')

        text_widget.see(match_start)

    def get_akamai_cname(self, domain):
        current_domain = domain
        akamai_domains = ['.edgekey.net', '.akamaiedge.net', '.edgesuite.net', '.akamaihd.net', '.akamai.net']
        
        for _ in range(5):
            try:
                answers = dns.resolver.resolve(current_domain, 'CNAME')
                if answers:
                    target = answers[0].target.to_text().rstrip('.')
                    if any(ak_dom in target for ak_dom in akamai_domains):
                        return target
                    current_domain = target
            except Exception:
                break
        return None

    def enforce_env_suffix(self, host, is_staging):
        if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
            return host
        
        akamai_suffixes = [
            ('.edgekey.net', '.edgekey-staging.net'),
            ('.akamaiedge.net', '.akamaiedge-staging.net'),
            ('.edgesuite.net', '.edgesuite-staging.net'),
            ('.akamaihd.net', '.akamaihd-staging.net'),
            ('.akamai.net', '.akamai-staging.net')
        ]
        
        for prod, staging in akamai_suffixes:
            if is_staging:
                if prod in host and staging not in host:
                    host = host.replace(prod, staging)
            else:
                if staging in host:
                    host = host.replace(staging, prod)
        return host

    def send_request(self):
        url = self.url_entry.get("1.0", tk.END).strip()
        method = self.method_var.get()
        http_version = self.http_var.get()
        network_choice = self.network_var.get()
        use_pragma = self.pragma_var.get()
        fetch_body = self.show_body_var.get()
        ignore_cert = self.ignore_cert_var.get()
        payload = self.payload_text.get("1.0", tk.END).strip()
        user_target = self.edge_ip_entry.get().strip()

        self.clear_search_highlights()
        self.response_text.delete("1.0", tk.END)
        self.body_text.delete("1.0", tk.END)
        self.cert_text.delete("1.0", tk.END)
        self.cert_decoded_text.delete("1.0", tk.END)
        self.curl_text.delete("1.0", tk.END)
        self.config_label.config(text="Config / CP Code: N/A")
        self.target_label.config(text="Routed to: Calculating...")
        self.root.update()

        parsed_url = urlparse(url)
        domain = parsed_url.netloc.split(':')[0]
        
        is_staging = "staging" in network_choice.lower()
        is_essl = "enhanced" in network_choice.lower()

        headers = {}

        if custom_hdrs_raw := self.headers_text.get("1.0", tk.END).strip():
            hdrs_list = re.split(r'[\n,]', custom_hdrs_raw)
            for h in hdrs_list:
                if ':' in h:
                    k, v = h.split(':', 1)
                    headers[k.strip()] = v.strip()

        if use_pragma:
            headers['Pragma'] = (
                "akamai-x-cache-on, akamai-x-cache-remote-on, "
                "akamai-x-check-cacheable, akamai-x-get-cache-key, "
                "akamai-x-get-extracted-values, akamai-x-get-ssl-client-session-id, "
                "akamai-x-get-true-cache-key, akamai-x-serial-no, akamai-x-get-request-id"
            )

        target_host = user_target
        routing_method = "User Override"

        if not target_host:
            akamai_cname = self.get_akamai_cname(domain)
            if akamai_cname:
                cname_is_essl = '.edgekey' in akamai_cname or '.akamaiedge' in akamai_cname
                cname_is_std = '.edgesuite' in akamai_cname or '.akamai.net' in akamai_cname or '.akamaihd' in akamai_cname

                if (is_essl and cname_is_essl) or (not is_essl and cname_is_std):
                    target_host = akamai_cname
                    routing_method = "Auto-CNAME Match"
                else:
                    routing_method = "Default Map (Network Mismatch)"
                    target_host = "e19.dscg.akamaiedge.net" if is_essl else "a1.g.akamai.net"
            else:
                routing_method = "Default Map (No CNAME)"
                target_host = "e19.dscg.akamaiedge.net" if is_essl else "a1.g.akamai.net"

        target_host = self.enforce_env_suffix(target_host, is_staging)

        try:
            target_ip = socket.gethostbyname(target_host)
            self.target_label.config(text=f"Routed to: {target_host} ({target_ip}) via {routing_method}")
        except socket.gaierror:
            self.target_label.config(text=f"Routed to: {target_host} (DNS Resolution Failed!)")
            self.response_text.insert(tk.END, f"Error: Could not resolve target {target_host} to an IP address.")
            return

        port = "443" if parsed_url.scheme == "https" else "80"

        if parsed_url.scheme == "https":
            try:
                openssl_cmd = [
                    "openssl", "s_client", "-showcerts",
                    "-connect", f"{target_ip}:443",
                    "-servername", parsed_url.netloc
                ]
                self.cert_text.insert(tk.END, f"Executing: {' '.join(openssl_cmd)}\n\n")
                
                cert_process = subprocess.run(openssl_cmd, input='', capture_output=True, text=True, timeout=10)
                
                if cert_process.stdout:
                    self.cert_text.insert(tk.END, cert_process.stdout)
                    pem_match = re.search(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", cert_process.stdout, re.DOTALL)
                    if pem_match:
                        x509_cmd = ["openssl", "x509", "-text", "-noout"]
                        x509_process = subprocess.run(x509_cmd, input=pem_match.group(0), capture_output=True, text=True, timeout=5)
                        if x509_process.stdout:
                            self.cert_decoded_text.insert(tk.END, x509_process.stdout)
                    else:
                        self.cert_decoded_text.insert(tk.END, "No PEM certificate block found to decode.")
            except Exception as e:
                self.cert_text.insert(tk.END, f"Failed to retrieve certificate: {str(e)}")
        else:
            self.cert_text.insert(tk.END, "Not applicable for HTTP requests.")

        self.root.update()

        body_file = tempfile.NamedTemporaryFile(delete=False).name
        curl_args = ["curl", "-s", "-D", "-", "-o", body_file, "-X", method]
        
        if ignore_cert:
            curl_args.append("-k")
            
        if http_version == "HTTP/2":
            curl_args.append("--http2")
        elif http_version == "HTTP/3":
            curl_args.append("--http3")
        else:
            curl_args.append("--http1.1")
            
        for k, v in headers.items():
            if k.lower() != 'host':
                curl_args.extend(["-H", f"{k}: {v}"])
                
        if payload and method in ['POST', 'PUT']:
            curl_args.extend(["-d", payload])
            
        curl_args.extend(["--resolve", f"{parsed_url.netloc}:{port}:{target_ip}"])
        curl_args.append(url)

        display_cmd = f"curl {'-k ' if ignore_cert else ''}-i -X {method} \\\n"
        if http_version == "HTTP/2": display_cmd += "  --http2 \\\n"
        if http_version == "HTTP/3": display_cmd += "  --http3 \\\n"
        for k, v in headers.items():
            if k.lower() != 'host':
                display_cmd += f"  -H '{k}: {v}' \\\n"
        if payload and method in ['POST', 'PUT']:
            display_cmd += f"  -d '{payload}' \\\n"
        display_cmd += f"  --resolve {parsed_url.netloc}:{port}:{target_ip} \\\n"
        display_cmd += f"  '{url}'"

        self.curl_text.insert(tk.END, "--- Equivalent Native CURL Command ---\n")
        self.curl_text.insert(tk.END, display_cmd + "\n\n")

        try:
            process = subprocess.run(curl_args, capture_output=True, text=True, timeout=15)
            
            if process.stderr:
                self.curl_text.insert(tk.END, "--- CURL STDERR ---\n" + process.stderr)

            self.response_text.insert(tk.END, process.stdout)

            headers_parsed = {}
            for line in process.stdout.splitlines():
                if ':' in line:
                    k, v = line.split(':', 1)
                    headers_parsed[k.strip().lower()] = v.strip()

            if 'x-cache-key' in headers_parsed:
                parts = headers_parsed['x-cache-key'].split('/')
                if len(parts) > 4:
                    self.config_label.config(text=f"Config / CP Code: {parts[3]}")

            if fetch_body:
                content_type = headers_parsed.get('content-type', '').lower()
                # Added 'mpegurl' and 'm3u8' to support text-based video playlists
                if any(t in content_type for t in ['text', 'json', 'xml', 'javascript', 'html', 'mpegurl', 'm3u8']):
                    with open(body_file, 'r', encoding='utf-8', errors='replace') as f:
                        self.body_text.insert(tk.END, f.read())
                    self.notebook.select(self.tab_body)
                    
                    if self.search_frame.winfo_ismapped():
                        self.perform_search()
                else:
                    self.body_text.insert(tk.END, f"Detected Binary Content ({content_type}).\nPrompting to save file...")
                    file_path = filedialog.asksaveasfilename(title="Save Binary Response", defaultextension=".bin")
                    if file_path:
                        shutil.copy2(body_file, file_path)
                        self.body_text.insert(tk.END, f"\n\nSuccess! File saved to:\n{file_path}")
            else:
                self.body_text.insert(tk.END, "Response body was not requested. Check 'Save/Show Body' to fetch it.")

        except Exception as e:
            self.response_text.insert(tk.END, f"Execution Error: {str(e)}")
            
        finally:
            if os.path.exists(body_file):
                os.remove(body_file)

if __name__ == "__main__":
    root = tk.Tk()
    app = AkaCurlApp(root)
    root.mainloop()