import javax.swing.*;
import javax.swing.table.DefaultTableModel;
import java.awt.*;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import org.json.*;

public class ClienteJWT extends JFrame {

    // Campos de configuración y autenticación
    private JTextField hostField, portField, userField, emailField, searchField;
    private JPasswordField passField;
    private JTextArea logArea;
    private JPanel semaforo;
    private JSONObject config;
    private JTable tablaLibros;

    public ClienteJWT() {
        setTitle("Cliente Microservicio JWT - Swing");
        setSize(1100, 720);
        setDefaultCloseOperation(EXIT_ON_CLOSE);
        setLayout(new BorderLayout());

        config = loadConfig();

        JPanel top = new JPanel(new FlowLayout(FlowLayout.LEFT));
        top.add(new JLabel("Host:"));
        hostField = new JTextField(config.optString("host", "http://127.0.0.1"), 20);
        top.add(hostField);
        top.add(new JLabel("Puerto:"));
        portField = new JTextField(String.valueOf(config.optInt("port", 5000)), 6);
        top.add(portField);

        JButton btnGuardar = new JButton("Guardar Configuración");
        btnGuardar.addActionListener(e -> saveConfig());
        top.add(btnGuardar);

        semaforo = new JPanel(new GridLayout(1, 3, 4, 4));
        for (int i = 0; i < 3; i++) {
            JPanel c = new JPanel();
            c.setBackground(Color.GRAY);
            semaforo.add(c);
        }
        top.add(semaforo);

        JButton btnHealth = new JButton("Checar /Health");
        btnHealth.addActionListener(e -> verificarHealth());
        top.add(btnHealth);

        add(top, BorderLayout.NORTH);

        // --- Pestañas ---
        JTabbedPane tabs = new JTabbedPane();
        tabs.add("Autenticación", crearPanelAuth());
        tabs.add("Acciones protegidas", crearPanelProtected());
        tabs.add("Tokens y Libros", crearPanelLibros());
        add(tabs, BorderLayout.CENTER);

        // --- Log ---
        logArea = new JTextArea();
        logArea.setEditable(false);
        JScrollPane scroll = new JScrollPane(logArea);
        scroll.setBorder(BorderFactory.createTitledBorder("Log del microservicio / cliente"));
        add(scroll, BorderLayout.SOUTH);

        appendLog("Aplicación iniciada. Config cargada de config.json");
    }

    // ==== Paneles ====

    private JPanel crearPanelAuth() {
        JPanel p = new JPanel(new GridLayout(1, 2, 20, 0));

        // --- Login ---
        JPanel login = new JPanel(new GridLayout(4, 2, 5, 5));
        login.setBorder(BorderFactory.createTitledBorder("Login"));
        login.add(new JLabel("Usuario:"));
        userField = new JTextField();
        login.add(userField);
        login.add(new JLabel("Contraseña:"));
        passField = new JPasswordField();
        login.add(passField);
        JButton btnLogin = new JButton("Iniciar sesión");
        btnLogin.addActionListener(e -> login());
        login.add(new JLabel());
        login.add(btnLogin);

        // --- Registro ---
        JPanel register = new JPanel(new GridLayout(5, 2, 5, 5));
        register.setBorder(BorderFactory.createTitledBorder("Registro"));
        register.add(new JLabel("Usuario:"));
        JTextField userReg = new JTextField();
        register.add(userReg);
        register.add(new JLabel("Email:"));
        emailField = new JTextField();
        register.add(emailField);
        register.add(new JLabel("Contraseña:"));
        JPasswordField passReg = new JPasswordField();
        register.add(passReg);
        JButton btnRegister = new JButton("Registrar");
        btnRegister.addActionListener(
                ev -> registrar(userReg.getText(), emailField.getText(), new String(passReg.getPassword())));
        register.add(new JLabel());
        register.add(btnRegister);

        p.add(login);
        p.add(register);
        return p;
    }

    private JPanel crearPanelProtected() {
        JPanel p = new JPanel(new GridLayout(2, 2, 10, 10));
        JButton btnProtected = new JButton("GET /protected");
        btnProtected.addActionListener(e -> getProtected());
        JButton btnRefresh = new JButton("POST /refresh");
        btnRefresh.addActionListener(e -> refreshToken());
        JButton btnClear = new JButton("Limpiar Sesión");
        btnClear.addActionListener(e -> limpiarSesion());
        JButton btnTokens = new JButton("Mostrar Tokens");
        btnTokens.addActionListener(e -> mostrarTokens());
        p.add(btnProtected);
        p.add(btnRefresh);
        p.add(btnTokens);
        p.add(btnClear);
        return p;
    }

    private JPanel crearPanelLibros() {
        JPanel p = new JPanel(new BorderLayout());
        JPanel top = new JPanel(new FlowLayout(FlowLayout.LEFT));
        top.add(new JLabel("Buscar (q):"));
        searchField = new JTextField(20);
        top.add(searchField);
        JButton btnBuscar = new JButton("GET /books");
        btnBuscar.addActionListener(e -> getBooks(searchField.getText()));
        top.add(btnBuscar);
        p.add(top, BorderLayout.NORTH);

        String[] columnas = { "isbn", "book_id", "title", "author", "publisher", "year", "genre", "price", "stock",
                "format" };
        tablaLibros = new JTable(new DefaultTableModel(columnas, 0));
        p.add(new JScrollPane(tablaLibros), BorderLayout.CENTER);
        return p;
    }

    // ==== Funcionalidad ====

    private JSONObject loadConfig() {
        try {
            File f = new File("config.json");
            if (!f.exists()) {
                JSONObject def = new JSONObject();
                def.put("host", "http://127.0.0.1");
                def.put("port", 5000);
                def.put("access_token", "");
                def.put("refresh_token", "");
                try (FileWriter fw = new FileWriter(f)) {
                    fw.write(def.toString(2));
                }
                return def;
            }
            String txt = new String(java.nio.file.Files.readAllBytes(f.toPath()), StandardCharsets.UTF_8);
            return new JSONObject(txt);
        } catch (Exception e) {
            appendLog("Error cargando configuración: " + e);
            return new JSONObject();
        }
    }

    private void saveConfig() {
        try {
            config.put("host", hostField.getText().trim());
            config.put("port", Integer.parseInt(portField.getText().trim()));
            try (FileWriter fw = new FileWriter("config.json")) {
                fw.write(config.toString(2));
            }
            appendLog("Configuración guardada.");
        } catch (Exception e) {
            appendLog("Error guardando config: " + e.getMessage());
        }
    }

    private String baseUrl(String path) {
        return config.getString("host") + ":" + config.getInt("port") + path;
    }

    private void registrar(String user, String email, String pass) {
        try {
            URL url = new URL(baseUrl("/register"));
            HttpURLConnection c = (HttpURLConnection) url.openConnection();
            c.setRequestMethod("POST");
            c.setRequestProperty("Content-Type", "application/json");
            c.setDoOutput(true);
            String body = String.format("{\"username\":\"%s\",\"email\":\"%s\",\"password\":\"%s\"}", user, email,
                    pass);
            c.getOutputStream().write(body.getBytes(StandardCharsets.UTF_8));
            appendLog("[REGISTER] " + c.getResponseCode() + " " + new String(c.getInputStream().readAllBytes()));
        } catch (Exception e) {
            appendLog("[REGISTER] Error: " + e.getMessage());
        }
    }

    private void login() {
        try {
            URL url = new URL(baseUrl("/login"));
            HttpURLConnection c = (HttpURLConnection) url.openConnection();
            c.setRequestMethod("POST");
            c.setRequestProperty("Content-Type", "application/json");
            c.setDoOutput(true);
            String body = String.format("{\"username\":\"%s\",\"password\":\"%s\"}", userField.getText(),
                    new String(passField.getPassword()));
            c.getOutputStream().write(body.getBytes(StandardCharsets.UTF_8));
            int code = c.getResponseCode();
            appendLog("[LOGIN] " + code);
            if (code == 200) {
                String res = new String(c.getInputStream().readAllBytes());
                JSONObject data = new JSONObject(res);
                config.put("access_token", data.optString("access_token", ""));
                config.put("refresh_token", data.optString("refresh_token", ""));
                saveConfig();
                appendLog("Tokens guardados.");
            }
        } catch (Exception e) {
            appendLog("[LOGIN] Error: " + e.getMessage());
        }
    }

    private void getProtected() {
        try {
            URL url = new URL(baseUrl("/protected"));
            HttpURLConnection c = (HttpURLConnection) url.openConnection();
            c.setRequestProperty("Authorization", "Bearer " + config.optString("access_token", ""));
            appendLog("[PROTECTED] " + c.getResponseCode() + " " + new String(c.getInputStream().readAllBytes()));
        } catch (Exception e) {
            appendLog("[PROTECTED] Error: " + e.getMessage());
        }
    }

    private void refreshToken() {
        try {
            URL url = new URL(baseUrl("/refresh"));
            HttpURLConnection c = (HttpURLConnection) url.openConnection();
            c.setRequestMethod("POST");
            c.setRequestProperty("Authorization", "Bearer " + config.optString("refresh_token", ""));
            int code = c.getResponseCode();
            appendLog("[REFRESH] " + code);
            if (code == 200) {
                String res = new String(c.getInputStream().readAllBytes());
                JSONObject data = new JSONObject(res);
                config.put("access_token", data.optString("access_token", ""));
                saveConfig();
                appendLog("Access token actualizado.");
            }
        } catch (Exception e) {
            appendLog("[REFRESH] Error: " + e.getMessage());
        }
    }

    private void getBooks(String q) {
        try {
            String urlFull = baseUrl("/books" + (q.isEmpty() ? "" : "?q=" + q));
            URL url = new URL(urlFull);
            HttpURLConnection c = (HttpURLConnection) url.openConnection();
            c.setRequestProperty("Authorization", "Bearer " + config.optString("access_token", ""));
            int code = c.getResponseCode();
            String res = new String(c.getInputStream().readAllBytes());
            appendLog("[BOOKS] " + code);
            JSONArray arr = new JSONArray(res);
            DefaultTableModel model = (DefaultTableModel) tablaLibros.getModel();
            model.setRowCount(0);
            for (int i = 0; i < arr.length(); i++) {
                JSONObject o = arr.getJSONObject(i);
                Object[] row = new Object[10];
                int j = 0;
                for (String col : new String[] { "isbn", "book_id", "title", "author", "publisher", "year", "genre",
                        "price", "stock", "format" })
                    row[j++] = o.optString(col, "");
                model.addRow(row);
            }
        } catch (Exception e) {
            appendLog("[BOOKS] Error: " + e.getMessage());
        }
    }

    private void mostrarTokens() {
        appendLog("[TOKENS] Access=" + config.optString("access_token"));
        appendLog("[TOKENS] Refresh=" + config.optString("refresh_token"));
    }

    private void limpiarSesion() {
        config.put("access_token", "");
        config.put("refresh_token", "");
        saveConfig();
        appendLog("Sesión limpiada.");
    }

    private void verificarHealth() {
        try {
            URL url = new URL(baseUrl("/"));
            HttpURLConnection c = (HttpURLConnection) url.openConnection();
            int code = c.getResponseCode();
            appendLog("[HEALTH] " + code);
            for (Component comp : semaforo.getComponents())
                comp.setBackground(code == 200 ? Color.GREEN : Color.RED);
        } catch (Exception e) {
            appendLog("[HEALTH] Error: " + e.getMessage());
            for (Component comp : semaforo.getComponents())
                comp.setBackground(Color.RED);
        }
    }

    private void appendLog(String msg) {
        logArea.append("[" + java.time.LocalTime.now() + "] " + msg + "\n");
        logArea.setCaretPosition(logArea.getDocument().getLength());
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            ClienteJWT app = new ClienteJWT();
            app.setVisible(true);
        });
    }
}
