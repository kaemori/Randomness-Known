using System;
using System.Collections;
using System.IO;
using System.IO.Pipes;
using System.Threading;
using BepInEx;
using HarmonyLib;
using UnityEngine;
using UnityEngine.SceneManagement;
using Newtonsoft.Json.Linq;

using static System.Diagnostics.Stopwatch;

namespace ModNamespace
{
    internal static class PipeWriter
    {
        private static NamedPipeServerStream _pipe;
        private static StreamWriter _writer;
        private static bool _connected = false;
        private static Thread _thread;
        private static bool _shouldKeepRunning = true;
        private static long _lastConnectionTime = 0;
        private static long _lastDisconnectTime = 0;

        public static void Init()
        {
            Cleanup();
            _shouldKeepRunning = true;

            _thread = new Thread(() =>
            {
                while (_shouldKeepRunning)
                {
                    try
                    {
                        _pipe = new NamedPipeServerStream(
                            "unrandom_pipe",
                            PipeDirection.Out,
                            1,
                            PipeTransmissionMode.Byte,
                            PipeOptions.Asynchronous
                        );
                        Plugin.Logger.LogInfo("[PipeWriter] waiting for python...");
                        _pipe.WaitForConnection();
                        _writer = new StreamWriter(_pipe) { AutoFlush = true };
                        _connected = true;
                        _lastConnectionTime = GetTimestamp();
                        _lastDisconnectTime = 0;
                        Plugin.Logger.LogInfo("[PipeWriter] python connected!!");
                        SendBootState();
                    }
                    catch (Exception e)
                    {
                        Plugin.Logger.LogError($"[PipeWriter] init failed: {e}");
                        if (_shouldKeepRunning)
                        {
                            Thread.Sleep(1000);
                        }
                    }
                }
            });
            _thread.IsBackground = true;
            _thread.Start();
        }

        private static void SendBootState()
        {
            Send(new JObject
            {
                ["type"] = "boot",
                ["unity_version"] = Application.unityVersion,
                ["app_version"] = Application.version,
                ["platform"] = Application.platform.ToString(),
                ["scene"] = SceneManager.GetActiveScene().name,
                ["time"] = Time.realtimeSinceStartup,
                ["screen"] = $"{Screen.width}x{Screen.height}",
                ["target_framerate"] = Application.targetFrameRate,
                ["quality_level"] = QualitySettings.GetQualityLevel(),
            });
        }

        public static void Send(JObject obj)
        {
            if (!_connected) return;
            try
            {
                Plugin.Logger.LogInfo($"[PipeWriter] sending: {obj["type"]}");
                _writer.WriteLine(Newtonsoft.Json.JsonConvert.SerializeObject(obj));
            }
            catch
            {
                long currentTime = GetTimestamp();
                long timeSinceConnect = currentTime - _lastConnectionTime;

                if (_lastDisconnectTime != 0)
                {
                    long timeSinceLastDisconnect = currentTime - _lastDisconnectTime;
                    if (timeSinceLastDisconnect < 10000)
                    {
                        Plugin.Logger.LogError("[PipeWriter] Pipe disconnected again within 10 seconds - stopping plugin");
                        _shouldKeepRunning = false;
                        _connected = false;
                        Cleanup();
                        return;
                    }
                }

                _lastDisconnectTime = currentTime;
                _connected = false;
                Plugin.Logger.LogWarning($"[PipeWriter] python disconnected (connected for {timeSinceConnect}ms). Attempting to reconnect...");
                Cleanup();
            }
        }

        public static void Cleanup()
        {
            _connected = false;
            try { _writer?.Dispose(); } catch { }
            try { _pipe?.Dispose(); } catch { }
            _writer = null;
            _pipe = null;
        }
    }

    // ─── world blocks sender ───────────────────────────────────────────────────

    internal static class WorldBlocksSender
    {
        private static readonly System.Reflection.FieldInfo _worldBlocksField =
            typeof(WorldGeneration).GetField("worldBlocks",
                System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);

        public static void SendWorldBlocks()
        {
            var wg = WorldGeneration.world;
            if (wg == null)
            {
                Plugin.Logger.LogWarning("[WorldBlocksSender] world is null");
                return;
            }

            var worldBlocks = (ushort[,])_worldBlocksField.GetValue(wg);
            if (worldBlocks == null)
            {
                Plugin.Logger.LogWarning("[WorldBlocksSender] worldBlocks is null");
                return;
            }

            int w = worldBlocks.GetLength(0);
            int h = worldBlocks.GetLength(1);

            byte[] bytes = new byte[w * h * sizeof(ushort)];
            Buffer.BlockCopy(worldBlocks, 0, bytes, 0, bytes.Length);
            string b64 = Convert.ToBase64String(bytes);

            PipeWriter.Send(new JObject
            {
                ["type"] = "worldblocks",
                ["width"] = w,
                ["height"] = h,
                ["dtype"] = "uint16",
                ["biome_depth"] = wg.biomeDepth,
                ["data"] = b64,
            });

            Plugin.Logger.LogInfo($"[WorldBlocksSender] sent {w}x{h} worldBlocks ({bytes.Length} bytes raw)");
        }
    }

    internal class Patches
    {
        [HarmonyPatch(typeof(ConsoleScript))]
        internal static class ConsolePatch
        {
            [HarmonyPatch(nameof(ConsoleScript.Start))]
            [HarmonyPostfix]
            private static void StartPatch()
            {
                ConsoleScript.instance.LogToConsole(
                    $"Loaded {Plugin.ModName} (v{Plugin.ModVersion})");
            }
        }

        [HarmonyPatch(typeof(WorldGeneration), "FinishWorldGeneration")]
        internal static class FinishWorldGenerationPatch
        {
            [HarmonyPostfix]
            private static void Postfix(ref IEnumerator __result)
            {
                __result = Wrap(__result);
            }

            private static IEnumerator Wrap(IEnumerator original)
            {
                while (original.MoveNext())
                    yield return original.Current;

                WorldBlocksSender.SendWorldBlocks();
            }
        }
    }
}