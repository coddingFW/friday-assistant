// Ponto de entrada da aplicação Tauri. O frontend é um web app puro (React) que
// fala com o backend Friday via REST/WebSocket — o shell Tauri apenas o hospeda.

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("erro ao iniciar a aplicação Friday");
}
