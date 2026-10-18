using System;
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
    // ─── pipe writer ──────────────────────────────────────────────────────────

    internal static class PipeWriter
    {
        private static NamedPipeServerStream _pipe;
        private static StreamWriter _writer;
        private static bool _connected = false;
        private static Thread _thread;
        private static bool _shouldKeepRunning = true;
        private static long _lastConnectionTime = 0;
        private static long _lastDisconnectTime = 0;

        // Cached reflection field info for Random.State
        private static readonly System.Reflection.FieldInfo _s0Field;
        private static readonly System.Reflection.FieldInfo _s1Field;
        private static readonly System.Reflection.FieldInfo _s2Field;
        private static readonly System.Reflection.FieldInfo _s3Field;

        private static JArray GetCallStack()
        {
            var stack = new System.Diagnostics.StackTrace(skipFrames: 2, fNeedFileInfo: true);
            var frames = new JArray();
            foreach (System.Diagnostics.StackFrame frame in stack.GetFrames())
            {
                var method = frame.GetMethod();
                if (method == null) continue;

                var ns = method.DeclaringType?.Namespace ?? "";
                var typeName = method.DeclaringType?.Name ?? "";
                var methodName = method.Name;

                // Skip internals
                if (ns.StartsWith("HarmonyLib") || ns.StartsWith("BepInEx") ||
                    ns.StartsWith("System") || ns.StartsWith("MonoMod"))
                    continue;

                // Skip our own patch classes
                if (ns == "ModNamespace")
                    continue;

                // Clean up DMD<ClassName::MethodName> → ClassName.MethodName
                string label;
                if (methodName.Contains("DMD<") && methodName.Contains("::"))
                {
                    // extract string inside <> pair and replace :: with .
                    // i.e. WorldGeneration.DMD<WorldGeneration::Start> -> WorldGeneration.Start
                    int start = methodName.IndexOf('<') + 1;
                    int end = methodName.IndexOf('>');
                    string inner = methodName.Substring(start, end - start);
                    label = $"{inner.Replace("::", ".")}";
                }
                else
                {
                    label = $"{method.DeclaringType?.FullName}.{methodName}";
                }

                var fileName = frame.GetFileName();
                var line = frame.GetFileLineNumber();
                frames.Add(new JObject
                {
                    ["method"] = label,
                });

                if (frames.Count >= 20) break; // raised from 8
            }
            return frames;
        }

        static PipeWriter()
        {
            var t = typeof(UnityEngine.Random.State);
            _s0Field = t.GetField("s0", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            _s1Field = t.GetField("s1", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            _s2Field = t.GetField("s2", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            _s3Field = t.GetField("s3", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);

            if (_s0Field == null || _s1Field == null || _s2Field == null || _s3Field == null)
            {
                Plugin.Logger.LogError("[PipeWriter] Failed to cache Random.State fields!");
            }
        }

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
                            Thread.Sleep(1000); // Wait 1 second before retrying
                        }
                    }
                }
            });
            _thread.IsBackground = true;
            _thread.Start();
        }

        private static JObject GetState()
        {
            var s = UnityEngine.Random.state;
            return new JObject
            {
                ["s0"] = unchecked((uint)(int)_s0Field.GetValue(s)),
                ["s1"] = unchecked((uint)(int)_s1Field.GetValue(s)),
                ["s2"] = unchecked((uint)(int)_s2Field.GetValue(s)),
                ["s3"] = unchecked((uint)(int)_s3Field.GetValue(s)),
            };
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
                ["state"] = GetState(),
            });
        }

        public static void Send(JObject obj)
        {
            if (!_connected) return;
            try
            {
                // Plugin.Logger.LogInfo($"[PipeWriter] sending: {obj}");
                _writer.WriteLine(Newtonsoft.Json.JsonConvert.SerializeObject(obj));
            }
            catch
            {
                long currentTime = GetTimestamp();
                long timeSinceConnect = currentTime - _lastConnectionTime;

                if (_lastDisconnectTime != 0)
                {
                    // We already disconnected once recently
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

        public static void SendCall(string fn, JToken result)
        {
            // merge with SCWA, empty JObject
            SendCallWithArgs(fn, new JObject(), result);
        }

        public static void SendCallWithArgs(string fn, JObject args, JToken result)
        {
            Send(new JObject
            {
                ["type"] = "call",
                ["fn"] = fn,
                ["args"] = args,
                ["result"] = result,
                // ["stack"] = GetCallStack(),
                ["stack"] = { },
                ["state"] = GetState(),
            });
        }
    }

    // ─── patches ──────────────────────────────────────────────────────────────

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

        // ── random.range int ──

        [HarmonyPatch(typeof(UnityEngine.Random), nameof(UnityEngine.Random.Range),
            new[] { typeof(int), typeof(int) })]
        internal static class RandomRangeIntPatch
        {
            [HarmonyPostfix]
            private static void Postfix(int minInclusive, int maxExclusive, ref int __result)
            {
                PipeWriter.SendCallWithArgs("random.range.int",
                    new JObject { ["min"] = minInclusive, ["max"] = maxExclusive },
                    __result);
            }
        }

        // ── random.range float ──

        [HarmonyPatch(typeof(UnityEngine.Random), nameof(UnityEngine.Random.Range),
            new[] { typeof(float), typeof(float) })]
        internal static class RandomRangeFloatPatch
        {
            [HarmonyPostfix]
            private static void Postfix(float minInclusive, float maxInclusive, ref float __result)
            {
                PipeWriter.SendCallWithArgs("random.range.float",
                    new JObject { ["min"] = minInclusive, ["max"] = maxInclusive },
                    __result);
            }
        }

        // ── random.value ──

        [HarmonyPatch(typeof(UnityEngine.Random), "value", MethodType.Getter)]
        internal static class RandomValuePatch
        {
            [HarmonyPostfix]
            private static void Postfix(ref float __result)
            {
                PipeWriter.SendCall("random.value", __result);
            }
        }

        // ── random.insideunitcircle ──

        [HarmonyPatch(typeof(UnityEngine.Random), "insideUnitCircle", MethodType.Getter)]
        internal static class RandomInsideUnitCirclePatch
        {
            [HarmonyPostfix]
            private static void Postfix(ref Vector2 __result)
            {
                PipeWriter.SendCall("random.insideunitcircle",
                    new JObject { ["x"] = __result.x, ["y"] = __result.y });
            }
        }

        // ── random.colorhsv (all 4 overloads) ──

        [HarmonyPatch(typeof(UnityEngine.Random), nameof(UnityEngine.Random.ColorHSV),
            new Type[] { })]
        internal static class RandomColorHSV0
        {
            [HarmonyPostfix]
            private static void Postfix(ref Color __result)
            {
                PipeWriter.SendCall("random.colorhsv",
                    new JObject
                    {
                        ["r"] = __result.r,
                        ["g"] = __result.g,
                        ["b"] = __result.b,
                        ["a"] = __result.a
                    });
            }
        }

        [HarmonyPatch(typeof(UnityEngine.Random), nameof(UnityEngine.Random.ColorHSV),
            new[] { typeof(float), typeof(float) })]
        internal static class RandomColorHSV2
        {
            [HarmonyPostfix]
            private static void Postfix(float hueMin, float hueMax, ref Color __result)
            {
                PipeWriter.SendCallWithArgs("random.colorhsv",
                    new JObject { ["hueMin"] = hueMin, ["hueMax"] = hueMax },
                    new JObject
                    {
                        ["r"] = __result.r,
                        ["g"] = __result.g,
                        ["b"] = __result.b,
                        ["a"] = __result.a
                    });
            }
        }

        [HarmonyPatch(typeof(UnityEngine.Random), nameof(UnityEngine.Random.ColorHSV),
            new[] { typeof(float), typeof(float), typeof(float), typeof(float) })]
        internal static class RandomColorHSV4
        {
            [HarmonyPostfix]
            private static void Postfix(float hueMin, float hueMax,
                float saturationMin, float saturationMax, ref Color __result)
            {
                PipeWriter.SendCallWithArgs("random.colorhsv",
                    new JObject
                    {
                        ["hueMin"] = hueMin,
                        ["hueMax"] = hueMax,
                        ["saturationMin"] = saturationMin,
                        ["saturationMax"] = saturationMax
                    },
                    new JObject
                    {
                        ["r"] = __result.r,
                        ["g"] = __result.g,
                        ["b"] = __result.b,
                        ["a"] = __result.a
                    });
            }
        }

        [HarmonyPatch(typeof(UnityEngine.Random), nameof(UnityEngine.Random.ColorHSV),
            new[] { typeof(float), typeof(float), typeof(float), typeof(float),
                    typeof(float), typeof(float) })]
        internal static class RandomColorHSV6
        {
            [HarmonyPostfix]
            private static void Postfix(float hueMin, float hueMax,
                float saturationMin, float saturationMax,
                float valueMin, float valueMax, ref Color __result)
            {
                PipeWriter.SendCallWithArgs("random.colorhsv",
                    new JObject
                    {
                        ["hueMin"] = hueMin,
                        ["hueMax"] = hueMax,
                        ["saturationMin"] = saturationMin,
                        ["saturationMax"] = saturationMax,
                        ["valueMin"] = valueMin,
                        ["valueMax"] = valueMax
                    },
                    new JObject
                    {
                        ["r"] = __result.r,
                        ["g"] = __result.g,
                        ["b"] = __result.b,
                        ["a"] = __result.a
                    });
            }
        }
    }
}