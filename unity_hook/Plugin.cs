using System;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using BepInEx;
using BepInEx.Logging;
using HarmonyLib;
using MonoMod.RuntimeDetour;
using UnityEngine;
using CUCoreLib.ContentReload;
using CUCoreLib.Data;
using CUCoreLib.Helpers;
using CUCoreLib.Registries;
using CUCoreLib.Saving;
using Newtonsoft.Json.Linq;

namespace ModNamespace
{
    [BepInPlugin(ModGUID, ModName, ModVersion)]
    [BepInDependency("net.cucorelib", BepInDependency.DependencyFlags.HardDependency)]
    public class Plugin : BaseUnityPlugin
    {
        public const string ModGUID = "com.rayleigh.urandom";
        public const string ModName = "unrandom";
        public const string ModVersion = "0.0.1";

        internal static new ManualLogSource Logger;
        private readonly Harmony _harmony = new(ModGUID);
        public static Plugin Instance { get; private set; } = null!;

        public void Awake()
        {
            Logger = base.Logger;
            Instance = this;

            _harmony.PatchAll();
            Logger.LogInfo($"Plugin {ModName} is loaded!");

            DoStuff();
            ContentReloadManager.EnableHotReload(ModGUID);
            RegisterReloadable();
        }

        private void RegisterReloadable()
        {
            // awa
        }

        private void DoStuff()
        {
            PipeWriter.Init();
        }

        private void OnDestroy()
        {
            PipeWriter.Cleanup();
            _harmony.UnpatchSelf();
        }
    }
}
