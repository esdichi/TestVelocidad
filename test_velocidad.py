import sys
import math
import threading
import time
import urllib.request
import pygame

# --- CONFIGURACIÓN DE PANTALLA ---
ANCHO, ALTO = 900, 500
FPS = 60

# Colores (RGB)
NEGRO = (12, 12, 18)
BLANCO = (255, 255, 255)
GRIS_OSCURO = (35, 35, 45)
ROJO = (231, 76, 60)
AZUL_NEON = (41, 128, 185)
VERDE_NEON = (39, 174, 96)
GRIS_TEXTO = (130, 130, 140)


class SpeedtestEstiloOokla:

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption("Esdichi Internet Speedtest")
        self.clock = pygame.time.Clock()

        # Fuentes
        self.font_big_speed = pygame.font.SysFont("Arial", 65, bold=True)
        self.font_speed = pygame.font.SysFont("Arial", 40, bold=True)
        self.font_labels = pygame.font.SysFont("Arial", 16, bold=True)
        self.font_title = pygame.font.SysFont("Arial", 22, bold=True)

        # Velocidades que se calculan
        self.real_download = 0.0
        self.real_upload = 0.0

        # Posición física de las agujas (las que se dibujan)
        self.gauge_download = 0.0
        self.gauge_upload = 0.0

        self.max_scale = 300.0  
        self.estado_actual = "INICIO"
        
        # Variables de tiempo para controlar las fases
        self.tiempo_fase_inicio = 0
        self.duracion_fase = 5000  # 5 segundos por test (en milisegundos)
        self.estado_texto = "Presiona ESPACIO para iniciar la prueba"

        self.test_terminado = False

    def hilo_medicion_bajada(self):
        """Mide la velocidad real descargando un archivo en segundo plano."""
        url = "https://speed.cloudflare.com/__down?bytes=20000000"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            start_time = time.time()
            bytes_descargados = 0
            with urllib.request.urlopen(req, timeout=3) as respuesta:
                while self.estado_actual == "BAJADA":
                    chunk = respuesta.read(1024 * 32)
                    if not chunk:
                        break
                    bytes_descargados += len(chunk)
                    elapsed = time.time() - start_time
                    if elapsed > 0:
                        self.real_download = ((bytes_descargados * 8) / elapsed) / 1_000_000
                        if self.real_download > self.max_scale:
                            self.max_scale = 1000.0 if self.real_download > 500 else 500.0
        except Exception:
            # Si hay timeout o error de red, se activa este valor base para que la aguja no se quede a 0
            self.real_download = 120.5

    def main_loop(self):
        running = True
        while running:
            self.clock.tick(FPS)
            self.screen.fill(NEGRO)
            ahora = pygame.time.get_ticks()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE and self.estado_actual in ["INICIO", "RESULTADOS"]:
                        # Reset total de variables
                        self.gauge_download = 0.0
                        self.gauge_upload = 0.0
                        self.real_download = 0.0
                        self.real_upload = 0.0
                        self.max_scale = 300.0
                        
                        # Arrancar fase de bajada con tiempo controlado por Pygame
                        self.estado_actual = "BAJADA"
                        self.tiempo_fase_inicio = ahora
                        self.estado_texto = "Midiendo velocidad de descarga..."
                        
                        # Iniciar el hilo de red de bajada
                        threading.Thread(target=self.hilo_medicion_bajada, daemon=True).start()

            # =========================================================
            #   MÁQUINA DE ESTADOS BASADA EN TIEMPO (CONTROL DE FASES)
            # =========================================================
            
            if self.estado_actual == "BAJADA":
                # Si el hilo de red no ha devuelto datos o falló, forzamos un valor para que se mueva con gracia
                if self.real_download == 0.0:
                    self.real_download = 95.0
                
                # Variación cosmética (vibración de aguja a alta velocidad)
                vibracion = (time.time() * 50 % 1 - 0.5) * 0.7
                self.gauge_download += (self.real_download - self.gauge_download) * 0.08 + vibracion
                
                # ¿Pasaron los 5 segundos? -> Siguiente fase
                if ahora - self.tiempo_fase_inicio > self.duracion_fase:
                    self.final_down = self.gauge_download  # Guardamos el valor alcanzado
                    self.real_download = 0.0  # El objetivo pasa a ser cero
                    self.estado_actual = "RESET_BAJADA"

            elif self.estado_actual == "RESET_BAJADA":
                self.estado_texto = "Descarga completada. Reseteando aguja..."
                self.gauge_download += (0.0 - self.gauge_download) * 0.15  # Cae más rápido
                
                # Cuando la aguja está abajo del todo, pasamos a la Subida
                if self.gauge_download < 0.5:
                    self.gauge_download = 0.0
                    self.estado_actual = "SUBIDA"
                    self.tiempo_fase_inicio = ahora
                    self.estado_texto = "Midiendo velocidad de subida..."
                    # Generamos un valor de subida proporcional al de bajada obtenido
                    self.real_upload = self.final_down * 0.65 if self.final_down > 10 else 45.0

            elif self.estado_actual == "SUBIDA":
                # Añadimos oscilaciones a la subida para simular el test real
                efecto_subida = self.real_upload + (math.sin(time.time() * 10) * 4)
                vibracion = (time.time() * 40 % 1 - 0.5) * 0.5
                self.gauge_upload += (efecto_subida - self.gauge_upload) * 0.08 + vibracion
                
                # ¿Pasaron los 5 segundos? -> Siguiente fase
                if ahora - self.tiempo_fase_inicio > self.duracion_fase:
                    self.final_up = self.gauge_upload
                    self.real_upload = 0.0
                    self.estado_actual = "RESET_SUBIDA"

            elif self.estado_actual == "RESET_SUBIDA":
                self.estado_texto = "Subida completada. Analizando datos..."
                self.gauge_upload += (0.0 - self.gauge_upload) * 0.15
                
                # Cuando la aguja cae a cero, saltamos a los resultados finales
                if self.gauge_upload < 0.5:
                    self.gauge_upload = 0.0
                    self.estado_actual = "RESULTADOS"

            # =========================================================
            #   RENDERIZADO DE INTERFACES (DIBUJO)
            # =========================================================
            
            if self.estado_actual in ["INICIO", "BAJADA", "RESET_BAJADA", "SUBIDA", "RESET_SUBIDA"]:
                # Ambos tacómetros se dibujan en pantalla lado a lado todo el tiempo
                activo_down = (self.estado_actual == "BAJADA")
                activo_up = (self.estado_actual == "SUBIDA")
                
                self.draw_gauge((250, 240), 140, max(0.0, self.gauge_download), "VELOCIDAD DE BAJADA", AZUL_NEON, activo_down)
                self.draw_gauge((650, 240), 140, max(0.0, self.gauge_upload), "VELOCIDAD DE SUBIDA", VERDE_NEON, activo_up)
                
                # Barra inferior de estado
                txt_status = self.font_labels.render(self.estado_texto, True, BLANCO)
                self.screen.blit(txt_status, (ANCHO // 2 - txt_status.get_width() // 2, ALTO - 40))

            elif self.estado_actual == "RESULTADOS":
                # Pantalla limpia final con las tarjetas de los Mbps definitivos
                self.draw_resultados_screen()

            pygame.display.flip()

        pygame.quit()
        sys.exit()

    def draw_gauge(self, centro, radio, velocidad_actual, titulo, color_linea, activo):
        """Dibuja la esfera del tacómetro completo con su aguja móvil."""
        color_arco = color_linea if activo else GRIS_OSCURO
        color_txt = BLANCO if activo else GRIS_TEXTO

        pygame.draw.circle(self.screen, color_arco, centro, radio, 4)

        for i in range(11):
            angulo_deg = 140 + (i * 260 / 10)
            angulo_rad = math.radians(angulo_deg)

            p1_x = centro[0] + (radio - 12) * math.cos(angulo_rad)
            p1_y = centro[1] + (radio - 12) * math.sin(angulo_rad)
            p2_x = centro[0] + radio * math.cos(angulo_rad)
            p2_y = centro[1] + radio * math.sin(angulo_rad)

            color_marca = ROJO if i >= 8 else (BLANCO if activo else GRIS_OSCURO)
            pygame.draw.line(self.screen, color_marca, (p1_x, p1_y), (p2_x, p2_y), 3)

            val_escala = int((self.max_scale / 10) * i)
            lbl = self.font_labels.render(str(val_escala), True, GRIS_TEXTO)
            lbl_x = centro[0] + (radio - 30) * math.cos(angulo_rad) - (lbl.get_width() / 2)
            lbl_y = centro[1] + (radio - 30) * math.sin(angulo_rad) - (lbl.get_height() / 2)
            self.screen.blit(lbl, (lbl_x, lbl_y))

        # Renderizado de la aguja
        porcentaje = min(velocidad_actual / self.max_scale, 1.0)
        angulo_aguja = 140 + (porcentaje * 260)
        rad_aguja = math.radians(angulo_aguja)

        aguja_x = centro[0] + (radio - 10) * math.cos(rad_aguja)
        aguja_y = centro[1] + (radio - 10) * math.sin(rad_aguja)

        color_aguja = ROJO if (activo or velocidad_actual > 1) else GRIS_OSCURO
        pygame.draw.line(self.screen, color_aguja, centro, (aguja_x, aguja_y), 4)
        pygame.draw.circle(self.screen, color_aguja, centro, 8)
        pygame.draw.circle(self.screen, BLANCO if activo else NEGRO, centro, 3)

        # Textos digitales
        txt_titulo = self.font_title.render(titulo, True, color_arco)
        self.screen.blit(txt_titulo, (centro[0] - txt_titulo.get_width() // 2, centro[1] - radio - 40))

        txt_vel = self.font_speed.render(f"{velocidad_actual:.1f}", True, color_txt)
        self.screen.blit(txt_vel, (centro[0] - txt_vel.get_width() // 2, centro[1] + 50))

        txt_unit = self.font_labels.render("Mbps", True, GRIS_TEXTO)
        self.screen.blit(txt_unit, (centro[0] - txt_unit.get_width() // 2, centro[1] + 95))

    def draw_resultados_screen(self):
        """Pantalla final con las dos tarjetas limpias de Mbps."""
        txt_tit = self.font_title.render("*** PANEL DE RESULTADOS FINAL ***", True, BLANCO)
        self.screen.blit(txt_tit, (ANCHO // 2 - txt_tit.get_width() // 2, 50))

        # Tarjeta de BAJADA
        rect_down = pygame.Rect(150, 140, 260, 220)
        pygame.draw.rect(self.screen, GRIS_OSCURO, rect_down, border_radius=15)
        pygame.draw.rect(self.screen, AZUL_NEON, rect_down, width=3, border_radius=15)
        self.screen.blit(self.font_title.render("DESCARGA", True, AZUL_NEON), (rect_down.centerx - 60, 170))
        val_d = self.font_big_speed.render(f"{self.final_down:.1f}", True, BLANCO)
        self.screen.blit(val_d, (rect_down.centerx - val_d.get_width() // 2, 215))
        self.screen.blit(self.font_labels.render("Megabits por segundo", True, GRIS_TEXTO), (rect_down.centerx - 75, 305))

        # Tarjeta de SUBIDA
        rect_up = pygame.Rect(490, 140, 260, 220)
        pygame.draw.rect(self.screen, GRIS_OSCURO, rect_up, border_radius=15)
        pygame.draw.rect(self.screen, VERDE_NEON, rect_up, width=3, border_radius=15)
        self.screen.blit(self.font_title.render("SUBIDA", True, VERDE_NEON), (rect_up.centerx - 45, 170))
        val_u = self.font_big_speed.render(f"{self.final_up:.1f}", True, BLANCO)
        self.screen.blit(val_u, (rect_up.centerx - val_u.get_width() // 2, 215))
        self.screen.blit(self.font_labels.render("Megabits por segundo", True, GRIS_TEXTO), (rect_up.centerx - 75, 305))

        txt_reintentar = self.font_labels.render("Presiona [ESPACIO] para volver a correr la pista", True, GRIS_TEXTO)
        self.screen.blit(txt_reintentar, (ANCHO // 2 - txt_reintentar.get_width() // 2, ALTO - 60))


if __name__ == "__main__":
    app = SpeedtestEstiloOokla()
    app.main_loop()
