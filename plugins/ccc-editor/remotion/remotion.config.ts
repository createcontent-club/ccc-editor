import {Config} from '@remotion/cli/config';

// Izlaz spreman za IG / TikTok / Shorts: H.264, yuv420p.
Config.setVideoImageFormat('jpeg');
Config.setCodec('h264');
Config.setPixelFormat('yuv420p');
Config.setOverwriteOutput(true);
// Prvo pokretanje Chrome-a na macOS-u (Gatekeeper provera) i spor eksterni disk
// mogu da probiju podrazumevanih 30 s za učitavanje fontova/videa.
Config.setDelayRenderTimeoutInMilliseconds(90_000);
