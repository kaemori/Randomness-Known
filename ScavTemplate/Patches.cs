using System;
using BepInEx;
using HarmonyLib;
using UnityEngine;
using CUCoreLib.Data;
using CUCoreLib.Helpers;
using CUCoreLib.Registries;
using CUCoreLib.Saving;

namespace ModNamespace
{
    internal class Patches
    {
        [HarmonyPatch(typeof(ConsoleScript))]
        internal static class ConsolePatch
        {
            [HarmonyPatch(nameof(ConsoleScript.Start))]
            [HarmonyPostfix]
            private static void StartPatch()
            {
                ConsoleScript.instance.LogToConsole($"Loaded {Plugin.ModName} (v{Plugin.ModVersion})");
            }
        }
    }
}
