import React, { useState, useEffect, useRef } from 'react';
import { Html5Qrcode } from 'html5-qrcode';
import { Camera } from '@capacitor/camera';
import { Capacitor } from '@capacitor/core';
import { ScannedCode, RouteData } from '../types';
import { ScannerSettings } from './useSettings';
import { playBeep, playErrorBeep } from '../utils/audio';

const MAX_CAMERA_RETRIES = 3;
const RETRY_DELAYS = [1000, 2000, 4000]; // backoff exponencial

export const useScanner = (
  isScannerActive: boolean,
  settings: ScannerSettings,
  setScannedCodes: React.Dispatch<React.SetStateAction<ScannedCode[]>>,
  loadedRoute: RouteData | null,
  onScanProcessed?: (code: ScannedCode) => void
) => {
  const [error, setError] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [hasFlash, setHasFlash] = useState(false);
  const [isFlashOn, setIsFlashOn] = useState(false);
  const [scanWarning, setScanWarning] = useState<string | null>(null);
  const [isForcingScan, setIsForcingScan] = useState(false);

  // lastScanned como useRef para evitar closure desatualizada no callback
  const lastScannedRef = useRef<string | null>(null);
  const [lastScannedDisplay, setLastScannedDisplay] = useState<string | null>(null);

  const html5QrCodeRef = useRef<Html5Qrcode | null>(null);
  const settingsRef = useRef(settings);
  const loadedRouteRef = useRef(loadedRoute);

  useEffect(() => {
    settingsRef.current = settings;
  }, [settings]);

  useEffect(() => {
    loadedRouteRef.current = loadedRoute;
  }, [loadedRoute]);

  useEffect(() => {
    let isMounted = true;
    let html5QrCode: Html5Qrcode | null = null;
    let retryCount = 0;
    let retryTimeout: ReturnType<typeof setTimeout> | null = null;

    const startScanner = async () => {
      try {
        const element = document.getElementById('reader');
        if (!element) return;

        // Request camera permission on native platform before starting
        if (Capacitor.isNativePlatform()) {
          try {
            const permResult = await Camera.requestPermissions({ permissions: ['camera'] });
            if (!permResult.camera || permResult.camera === 'prompt' || permResult.camera === 'denied') {
              setError("Permissão de câmera negada. Abra as configurações do app e permita o acesso à câmera.");
              return;
            }
          } catch (permErr) {
            console.error("Camera permission error:", permErr);
            setError("Não foi possível obter permissão da câmera. Verifique as configurações do app.");
            return;
          }
        }

        html5QrCode = new Html5Qrcode('reader');
        html5QrCodeRef.current = html5QrCode;
        setError(null);

        await html5QrCode.start(
          {
            facingMode: "environment",
            width: { ideal: 1280 },
            height: { ideal: 720 },
            aspectRatio: 1.777777778
          },
          {
            fps: 30,
            qrbox: (viewfinderWidth: number, viewfinderHeight: number) => {
              const width = Math.max(Math.floor(viewfinderWidth * 0.85), 260);
              const height = Math.max(Math.floor(viewfinderHeight * 0.45), 130);
              return { width, height };
            },
            experimentalFeatures: {
              useBarCodeDetectorIfSupported: true
            }
          } as any,
          onScanSuccess,
          onScanFailure
        );

        if (isMounted) {
          setIsScanning(true);
          retryCount = 0; // reset no sucesso
          try {
            const cameraCapabilities = html5QrCode.getRunningTrackCapabilities();
            if (cameraCapabilities && (cameraCapabilities as any).torch) {
              setHasFlash(true);
            } else {
              setHasFlash(false);
            }
          } catch (e) {
            setHasFlash(false);
          }
        }
      } catch (err) {
        console.error("Error starting scanner:", err);
        if (isMounted) {
          setIsScanning(false);
          // Retry com limite maximo e backoff exponencial
          if (retryCount < MAX_CAMERA_RETRIES) {
            const delay = RETRY_DELAYS[retryCount] || 4000;
            retryCount++;
            retryTimeout = setTimeout(() => {
              if (isMounted && isScannerActive) {
                startScanner();
              }
            }, delay);
          } else {
            setError("Não foi possível iniciar a câmera após várias tentativas. Verifique as permissões.");
          }
        }
      }
    };

    if (isScannerActive) {
      startScanner();
    } else {
      setIsScanning(false);
      setHasFlash(false);
      setIsFlashOn(false);
      setError(null);
    }

    return () => {
      isMounted = false;
      if (retryTimeout) clearTimeout(retryTimeout);
      if (html5QrCode && html5QrCode.isScanning) {
        html5QrCode.stop().catch(err => console.error("Error stopping scanner:", err));
      }
    };
  }, [isScannerActive]);

  const isUrl = (text: string) => {
    try {
      new URL(text);
      return true;
    } catch (_) {
      return false;
    }
  };

  const onScanSuccess = (decodedText: string, decodedResult: any) => {
    // Usar ref para comparacao correta (evita closure desatualizada)
    if (decodedText === lastScannedRef.current) return;

    let processedText = decodedText;

    if (settingsRef.current.smartExtraction) {
      try {
        const parsed = JSON.parse(decodedText);
        if (parsed && typeof parsed === 'object' && parsed.id) {
          processedText = String(parsed.id);
        }
      } catch (e) {}
    }

    if (settingsRef.current.onlyNumbers) {
      processedText = processedText.replace(/\D/g, '');
    }

    let isValid = true;
    let matchedAddress = '';
    let matchedBuyer = '';
    let matchedPhone = '';

    const route = loadedRouteRef.current;
    if (route) {
      const allPackages = route.paradas.flatMap((stop) => stop.pacotes);
      isValid = allPackages.includes(processedText);

      if (isValid) {
        for (const stop of route.paradas) {
          if (stop.pacotes.includes(processedText)) {
            matchedAddress = stop.endereco;
            const contato = (stop.contatos || []).find((c: any) => c.pacote === processedText);
            if (contato) {
              matchedBuyer = contato.nome_comprador || '';
              matchedPhone = contato.telefone || '';
            }
            break;
          }
        }
      }
    }

    if (settingsRef.current.sound) {
      if (route) {
        if (isValid) playBeep();
        else playErrorBeep();
      } else {
        playBeep();
      }
    }

    const newCode: ScannedCode = {
      id: crypto.randomUUID(),
      code: processedText,
      format: decodedResult?.result?.format?.formatName || "QR_CODE",
      timestamp: Date.now(),
      isValid: route ? isValid : undefined,
      address: matchedAddress,
      buyerName: matchedBuyer || undefined,
      phone: matchedPhone || undefined
    };

    if (settingsRef.current.avoidDuplicates) {
      setScannedCodes(prev => {
        const existingIndex = prev.findIndex(item => item.code === processedText);
        if (existingIndex !== -1) {
          const updated = [...prev];
          const [existing] = updated.splice(existingIndex, 1);
          return [{ ...existing, timestamp: Date.now(), isValid, address: matchedAddress, buyerName: matchedBuyer || undefined, phone: matchedPhone || undefined }, ...updated];
        }
        return [newCode, ...prev].slice(0, 500);
      });
    } else {
      setScannedCodes(prev => [newCode, ...prev].slice(0, 500));
    }

    // Atualizar ref e display
    lastScannedRef.current = decodedText;
    setLastScannedDisplay(decodedText);

    // Notificar componente pai sobre o scan processado
    if (onScanProcessed) {
      onScanProcessed(newCode);
    }

    if (settingsRef.current.autoOpenLinks && isUrl(processedText)) {
      window.open(processedText, '_blank');
    }

    setTimeout(() => {
      lastScannedRef.current = null;
      setLastScannedDisplay(null);
    }, settingsRef.current.scanInterval);

    if (settingsRef.current.vibration && window.navigator.vibrate) {
      if (route && !isValid) window.navigator.vibrate([200, 100, 200]);
      else window.navigator.vibrate(150);
    }
  };

  const onScanFailure = (_error: any) => {};

  const toggleFlash = async () => {
    if (!html5QrCodeRef.current || !hasFlash) return;
    try {
      const newState = !isFlashOn;
      await html5QrCodeRef.current.applyVideoConstraints({
        advanced: [{ torch: newState } as any]
      });
      setIsFlashOn(newState);
    } catch (err) {
      console.error("Flash toggle failed", err);
    }
  };

  const scanFile = async (file: File) => {
    if (!html5QrCodeRef.current) return false;
    try {
      const result = await html5QrCodeRef.current.scanFile(file, true);
      onScanSuccess(result, { result: { format: { formatName: 'FILE' } } });
      return true;
    } catch (err) {
      return false;
    }
  };

  return {
    error,
    isScanning,
    hasFlash,
    isFlashOn,
    toggleFlash,
    lastScanned: lastScannedDisplay,
    scanWarning,
    isForcingScan,
    setIsForcingScan,
    html5QrCodeRef,
    onScanSuccess,
    scanFile
  };
};
