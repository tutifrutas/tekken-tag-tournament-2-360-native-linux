#pragma once

#include <rex/cvar.h>
#include <rex/rex_app.h>
#include <rex/system/interfaces/graphics.h>
#include <rex/ui/window.h>

// TTT2 owns its guest resolution and state. Tekken 6 hooks must not be reused.
class Ttt2App final : public rex::ReXApp {
 public:
  using rex::ReXApp::ReXApp;

  static std::unique_ptr<rex::ui::WindowedApp> Create(
      rex::ui::WindowedAppContext& ctx) {
    return std::unique_ptr<Ttt2App>(new Ttt2App(ctx, "ttt2", PPCImageConfig));
  }

 protected:
  void OnCreateDialogs(rex::ui::ImGuiDrawer* drawer) override {
    rex::ReXApp::OnCreateDialogs(drawer);
    SetGuestFrameStats([this] {
      rex::ui::FrameStats result;
      result.internal_label = "Internal framebuffer";
      const auto* app_runtime = runtime();
      const auto* graphics = app_runtime ? app_runtime->graphics_system() : nullptr;
      if (graphics) {
        const auto stats = graphics->guest_frame_stats();
        result.frame_time_ms = stats.frame_time_ms;
        result.fps = stats.fps;
        result.frame_count = stats.frame_count;
        result.render_scale_x = stats.draw_resolution_scale_x;
        result.render_scale_y = stats.draw_resolution_scale_y;
        result.internal_width = stats.framebuffer_width;
        result.internal_height = stats.framebuffer_height;
      }
      // Report the measured framebuffer, not a guessed pre-upscale scene size.
      if (const auto* app_window = window()) {
        result.output_width = app_window->GetActualPhysicalWidth();
        result.output_height = app_window->GetActualPhysicalHeight();
      }
      return result;
    });
  }

  void OnConfigurePaths(rex::PathConfig& paths) override {
    // update: is the mounted TU3 package only (data100.bin expanded + data100.ofs).
    // TTT2 probes update:\\nrfo.bin first; finding the disc's nrfo there makes it
    // index data100.bin with the disc table, so every TU3 asset reads garbage.
    if (paths.update_data_root.empty()) paths.update_data_root = paths.game_data_root / "update";
  }

  void OnPostSetup() override {
    rex::ReXApp::OnPostSetup();
    // Costume baking reads GPU-resolved textures on the CPU. Apply this only
    // after the GPU plugin registers its flags; keep explicit user overrides.
    if (rex::cvar::GetFlagSource("readback_resolve") == rex::cvar::Source::kDefault) {
      rex::cvar::SetFlagByName("readback_resolve", "full");
    }
  }

  void OnPreSetup(rex::RuntimeConfig& config) override {
    if (config.gpu_plugin.empty()) config.gpu_plugin = "xenos";
  }
};
