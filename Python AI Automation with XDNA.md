# **Architectural Blueprint for Voice-Driven Heterogeneous Computing on AMD Strix Halo: Integrated Automation via Ryzen AI and Linux Input Subsystems**

## **1\. Executive Summary and Strategic Overview**

The convergence of high-performance mobile computing and edge artificial intelligence has culminated in the release of the AMD Strix Halo architecture, a platform that fundamentally alters the landscape of local inference capabilities. Specifically, the MS-S1 platform, housing the Ryzen AI Max processor series, introduces the XDNA 2 Neural Processing Unit (NPU), a dedicated silicon block capable of delivering up to 50 TOPS (Trillions of Operations Per Second) of AI compute power.1 This report presents a comprehensive architectural and implementation strategy for leveraging this hardware to build a latency-sensitive, Python-based voice automation system within the CachyOS (Arch Linux) environment using the Wayland display protocol.  
The core objective is to offload the computationally intensive task of continuous speech recognition from the General Purpose CPU (Zen 5\) and the Integrated GPU (RDNA 3.5) to the power-efficient NPU. This ensures that system resources remain available for the primary workload—whether that be gaming, compilation, or content creation—while maintaining a sophisticated voice control layer. By integrating the Ryzen AI software stack with the Linux uinput kernel subsystem, the proposed solution achieves rigorous OS-level automation that bypasses the security restrictions typically imposed by Wayland compositors.  
This document serves as an exhaustive technical manual and development guide. It synthesizes disparate information regarding the nascent Linux support for AMD’s XDNA architecture, the complexities of the Vitis AI execution flow, and the low-level mechanics of input emulation. The report culminates in a set of precise, context-aware prompts designed for use with AI coding assistants (GitHub Copilot), enabling the rapid scaffolding of a production-grade automation framework.

### **1.1 Architectural Vision and Component Hierarchy**

The proposed system is architected as an asynchronous pipeline that decouples data acquisition from inference and actuation. This separation of concerns is critical for maintaining system responsiveness and preventing the "blocking" behavior often seen in synchronous voice loops.

| System Layer | Component | Technology Stack | Hardware Target | Functionality |
| :---- | :---- | :---- | :---- | :---- |
| **Layer 1: Acquisition** | Audio Buffer & VAD | sounddevice (ALSA), webrtcvad, numpy | CPU (Core 0\) | Captures raw audio, filters silence/noise, creates discrete speech frames. |
| **Layer 2: Inference** | Speech-to-Text Engine | ONNX Runtime, Vitis AI EP, Quantized Whisper | NPU (XDNA 2\) | Converts audio frames into text tokens using hardware acceleration. |
| **Layer 3: Logic** | Command Parser | Python match/case, NLP Heuristics | CPU (Core 1\) | Maps transcribed text to specific semantic actions or macros. |
| **Layer 4: Actuation** | Event Injection | python-evdev, uinput, Virtual Gamepad | Kernel Space | Injects synthetic input events (keyboard, mouse, Xbox controller) into the kernel. |

## **2\. Hardware Foundation: The Strix Halo Compute Complex**

Understanding the underlying hardware is prerequisite to optimizing the software stack. The Strix Halo is not merely a faster APU; it is a heterogeneous compute complex where memory management and thermal constraints differ significantly from traditional desktop architectures.

### **2.1 The XDNA 2 Neural Processing Unit**

The XDNA 2 architecture represents a departure from the SIMD (Single Instruction, Multiple Data) parallelism of GPUs. It utilizes a spatial dataflow architecture consisting of a 2D array of AI Engine (AIE) tiles.4 Each tile possesses its own local memory and vector processor, connected by a high-bandwidth interconnect.

* **Dataflow Efficiency:** In a voice automation context, this architecture allows the Whisper model's layers to be mapped physically across the tile array. Audio data flows through the array in a pipelined fashion, drastically reducing the memory bandwidth pressure on the main system RAM compared to CPU or GPU inference. This results in significantly lower power consumption—often under 2 watts for the NPU subsystem—preserving battery life on mobile workstations.5  
* **Throughput vs. Latency:** While XDNA 2 excels at throughput (tokens per second), latency (time to first token) is dominated by the time required to load the instruction graph into the AIE tiles. The proposed software architecture mitigates this by maintaining a persistent ONNX session, preventing the costly re-initialization of the hardware context for every voice command.7

### **2.2 Unified Memory and the IOMMU**

The MS-S1 platform employs a unified memory architecture where the CPU, GPU, and NPU share a massive pool of LPDDR5X memory (often up to 128GB on Strix Halo). However, the NPU accesses this memory through the IOMMU (Input-Output Memory Management Unit) via the amdxdna kernel driver.9

* **Implication for Python:** Standard Python objects and even standard NumPy arrays are pageable memory. If the OS swaps these pages out or moves them during an NPU Direct Memory Access (DMA) operation, a fault occurs. The Vitis AI Execution Provider handles the necessary pinning and cache flushing, but the developer must ensure that input tensors fed to ONNX Runtime are contiguous in memory. Using numpy.ascontiguousarray() is a mandatory step in the audio pre-processing pipeline to ensure compatibility with the driver’s DMA requirements.

## **3\. The Operating System Environment: CachyOS on Strix Halo**

### **3.1 The Choice of CachyOS**

CachyOS is selected as the operating environment due to its aggressive optimization for modern x86-64 microarchitectures. Unlike generic distributions that compile for broad compatibility (generic x86-64), CachyOS repositories are compiled with x86-64-v4 instruction sets, leveraging AVX-512 capabilities present in the Zen 5 cores of the Strix Halo.10

* **Scheduler Optimizations:** The default inclusion of the BORE (Burst-Oriented Response Enhancer) or EEVDF (Earliest Eligible Virtual Deadline First) schedulers ensures that the interactive Python threads handling audio capture are prioritized over background system tasks. This reduces jitter in the audio buffer, which is critical for accurate voice activity detection.11  
* **AMD P-State Driver:** CachyOS enables the amd-pstate driver in active or guided mode by default. This allows the CPU to scale frequencies with much finer granularity and lower latency than the legacy ACPI driver, enabling the system to wake up from idle instantly when a voice command is detected.12

### **3.2 The Wayland Conundrum and the uinput Solution**

The transition to Wayland presents a fundamental challenge for automation utilities. The Wayland security model isolates applications, preventing them from snooping on or injecting input into other windows. Traditional X11 automation tools like xdotool or pyautogui rely on protocol extensions that are often restricted or non-functional in a secure Wayland session.14

* **Kernel-Level Bypass:** To achieve universal automation (controlling the OS shell, Steam games, and browser windows simultaneously), the solution must operate below the display server layer. The Linux kernel's uinput (User Level Input) module allows a userspace program to create a virtual character device (/dev/input/event\*) that indistinguishably mimics physical hardware.16  
* **Compositor Agnosticism:** Because the input events—keystrokes, mouse movements, and gamepad axis shifts—are generated at the kernel level, the Wayland compositor (whether KWin, Mutter, or Hyprland) perceives them as coming from a physical USB device. This completely circumvents the Wayland isolation protections, enabling the "god-mode" control required for a comprehensive voice assistant.

## **4\. Constructing the NPU Software Stack on Arch Linux**

A critical barrier identified in the research is the distribution gap: AMD officially validates and packages the Ryzen AI software stack for Ubuntu 24.04 and Fedora, leaving Arch Linux users to navigate a complex dependency chain manually.1 The following section details the precise synthesis of the NPU stack required for CachyOS.

### **4.1 The Driver Architecture: KMD and UMD**

The software stack for the NPU is bifurcated into the Kernel Mode Driver (KMD) and the User Mode Driver (UMD).

* **Kernel Mode Driver (amdxdna):** This component resides in the Linux kernel. It manages the hardware initialization, power gating, and memory mapping. Crucially, support for the XDNA NPU was mainlined in Linux kernel 6.14.7 Since CachyOS is a rolling release, it provides these newer kernels. Users must verify the driver status using dmesg | grep amdxdna to ensure the device file /dev/accel/accel0 is created.1  
* **User Mode Driver (XRT & Shim):** The userspace interface is provided by the Xilinx Runtime (XRT). However, XRT alone is insufficient; it requires a specific "shim" plugin (libamdxdna.so) to communicate with the amdxdna kernel module. This shim is effectively the translation layer that adapts generic FPGA-style calls from XRT into the specific ioctls understood by the Ryzen NPU.19

### **4.2 Installation Strategy for CachyOS**

Since .deb and .rpm packages cannot be natively installed, the solution leverages the Arch User Repository (AUR) and manual compilation.

1. **Firmware Extraction:** The NPU requires specific firmware blobs (17f0\_\*.bin for Strix Halo) located in /lib/firmware/amdnpu/. If the upstream linux-firmware package on CachyOS lags behind, these must be manually extracted from the AMD firmware git repository or the Ubuntu driver packages.18  
2. **XRT Compilation:** The xrt package must be compiled from source. The AUR package xrt or xrt-git handles this, but it is computationally expensive and requires significant build dependencies (boost, cmake, libncurses).  
3. **Shim Installation:** The amdxdna userspace driver (the shim) is available in the AUR as xrt-plugin-amdxdna (or similar variants like xrt-amd-xdna). Installing this ensures that XRT can actually "see" the NPU device managed by the kernel.19  
4. **Verification:** The utility xrt-smi acts as the primary diagnostic tool. Running xrt-smi examine should list the NPU device, confirming that both the KMD and UMD are correctly linked.22

### **4.3 The Python Middleware: ryzen-ai and ONNX Runtime**

To bridge Python with the C++ XRT stack, specific libraries are required.

* **ONNX Runtime Vitis AI:** The standard onnxruntime package on PyPI does *not* contain the Vitis AI Execution Provider. AMD distributes a fork or a plugin wheel (often named onnxruntime\_vitisai or similar) through their developer lounge.13  
* **The Vitis AI Execution Provider (VOE):** This component is the engine that compiles the ONNX graph into an XDNA executable (.xmodel). It relies on a configuration file (vaip\_config.json) and a binary overlay (.xclbin) that defines the NPU's configuration. For Strix Halo, the correct overlay is typically the 1x4 or 4x4 configuration found in the voe package assets.24  
* **Environmental Binding:** The environment variable XLNX\_VART\_FIRMWARE is the linchpin of this setup. It must point to the absolute path of the .xclbin file corresponding to the Strix Halo silicon (17f0). If this variable is unset or incorrect, the runtime will fail to initialize the NPU and silently fall back to the CPU, negating the project's goals.24

## **5\. Neural Inference Strategy: Whisper on the NPU**

The core workload of this project is Automatic Speech Recognition (ASR). The OpenAI Whisper model is the industry standard, but its raw computational cost is high. Adapting it for the Ryzen NPU requires specific optimization techniques.

### **5.1 Quantization and the "Quark" Flow**

The XDNA 2 NPU is optimized for low-precision arithmetic, specifically Integer 8 (Int8) and Block Float 16 (BF16). Running the standard Float32 Whisper model on the NPU is inefficient and often unsupported.

* **Int8 Quantization:** The model weights must be quantized to 8-bit integers. This reduces the memory footprint by 4x and dramatically increases throughput on the AIE tiles. AMD provides the "Quark" quantizer tool to perform this conversion, typically calibration on a small dataset to minimize accuracy loss.4  
* **Pre-Quantized Models:** AMD hosts pre-quantized versions of whisper-base and whisper-small in their Model Zoo on Hugging Face. Utilizing these pre-optimized models (e.g., amd/NPU-Whisper-Base-Small) is the recommended path to avoid the complexity of the quantization workflow.5

### **5.2 The Requirement for Static Shapes**

A defining characteristic of the current XDNA compiler stack is the requirement for static tensor shapes. The compiler generates a fixed dataflow graph that maps exactly to the AIE array. It cannot handle the variable-length sequences typical of natural language processing without recompilation.

* **Implication:** The audio input processing pipeline cannot simply pass "whatever audio was captured." It must strictly pad or truncate all audio input to a fixed duration—typically 30 seconds (or 480,000 samples at 16kHz). If a user speaks a 2-second command, the system must pad the remaining 28 seconds with silence before feeding it to the NPU. This ensures the input tensor matches the compiled graph's expectation (\`\` mel-spectrogram).5

### **5.3 ONNX Runtime Session Management**

The Python implementation interacts with the NPU via the onnxruntime API.

* **Execution Provider Priority:** The session must be initialized with the VitisAIExecutionProvider as the primary provider, followed by the CPUExecutionProvider as a fallback. This hybrid execution allows the NPU to handle the heavy matrix multiplications (Conv1d, MatMul) while the CPU handles unsupported operators (like specific activation functions or pre-processing steps) seamlessly.25  
* **Context Caching:** To mitigate the "warm-up" latency, the Vitis AI EP supports context caching. By defining a cache\_dir and cache\_key in the provider options, the compiled model binary is saved to disk. Subsequent application starts load this pre-compiled binary instantly, bypassing the just-in-time compilation phase.25

## **6\. The Linux Input Subsystem: Automation and Emulation**

With the AI interpretation layer defined, the focus shifts to the actuation layer: translating text into system inputs.

### **6.1 Understanding uinput Architecture**

The uinput driver is a kernel module that creates a character device /dev/uinput. When an application opens this device and writes specific data structures to it, the kernel creates a new virtual input node (e.g., /dev/input/eventX).

* **Kernel Integration:** Events injected into this node are processed by the kernel's input core exactly as if they originated from a USB HID driver. They traverse the evdev interface and are picked up by libinput (the input library used by Wayland compositors). This guarantees that the automation works universally across the desktop environment, including in games running under Proton/Wine.16

### **6.2 Virtual Controller Emulation (Xbox 360\)**

For gaming automation, emulating a generic joystick is insufficient. Modern games rely on the SDL2 gamepad database, which maps specific controller GUIDs to standardized layouts.

* **XInput Standard:** The virtual controller must emulate an Xbox 360 controller. This requires setting the virtual device's Vendor ID to 0x045e (Microsoft) and Product ID to 0x028e (Xbox 360 Controller).  
* **Axis Configuration:** The Xbox controller uses signed 16-bit integers for its analog sticks. A critical implementation detail often missed is the AbsInfo struct configuration. The X and Y axes must be defined with a minimum value of \-32768 and a maximum of 32767\. Setting these incorrectly (e.g., 0 to 255\) will cause the stick to drift or behave erratically in games.29  
* **Button Mapping:** The python-evdev library allows mapping standard Linux event codes (e.g., BTN\_SOUTH) to the controller's "A" button. The script acts as a translation layer, converting the semantic intent "Jump" into the electronic event EV\_KEY(BTN\_SOUTH, 1\) followed shortly by EV\_KEY(BTN\_SOUTH, 0).16

## **7\. Software Architecture & Concurrency Strategy**

The integration of these components requires a robust software architecture. A single-threaded script is non-viable; the blocking nature of audio recording would stall the inference engine, and the heavy compute of inference would cause audio buffer overruns (glitches).

### **7.1 Asynchronous Orchestration via asyncio**

The solution utilizes Python's asyncio library to manage concurrency.

* **The Audio Loop:** A dedicated thread (managed by sounddevice) continuously fills a lock-free ring buffer or a thread-safe asyncio.Queue with raw audio data. This ensures no audio frames are dropped regardless of the system load.31  
* **The Inference Worker:** A consumer coroutine monitors the queue. Upon detecting a silence threshold (via the webrtcvad library), it packages the accumulated audio. Because onnxruntime functions release the Global Interpreter Lock (GIL) but are blocking CPU operations, the actual session.run() call is offloaded to a ThreadPoolExecutor. This prevents the inference computation from freezing the event loop, allowing the system to continue listening or processing other inputs.32  
* **The Command Dispatcher:** Once text is returned, a lightweight parsing function matches the string against a predefined dictionary of actions and triggers the uinput event sequences.

### **7.2 Directory Structure and Scaffolding**

A structured project layout is essential for maintainability.

halo\_voice\_control/  
├── config/  
│   ├── vaip\_config.json        \# Vitis AI Compiler settings  
│   └── commands.yaml           \# User-definable voice macros  
├── models/  
│   ├── encoder\_int8.onnx       \# Quantized Whisper Encoder  
│   └── decoder\_int8.onnx       \# Quantized Whisper Decoder  
├── src/  
│   ├── audio\_engine.py         \# Async audio capture & VAD  
│   ├── inference\_engine.py     \# ONNX Runtime wrapper  
│   ├── input\_engine.py         \# uinput/evdev virtual device classes  
│   └── main.py                 \# Application entry point & orchestrator  
├── setup/  
│   ├── setup\_env.sh            \# Environment setup script  
│   └── 99-uinput.rules         \# Udev rules for permissions  
└── requirements.txt

## **8\. Implementation Guide: GitHub Copilot Prompts**

The following section provides the exact prompts to be fed into GitHub Copilot. These prompts are engineered to generate code that adheres to the specific constraints of the Strix Halo hardware and CachyOS environment.

### **8.1 Prompt Set 1: Environment & System Validation**

Context: "I am setting up a Python project on CachyOS for the AMD Strix Halo. I need to validate the NPU driver stack and set up the environment."  
Prompt:  
"Write a bash script named setup\_strix\_env.sh for an Arch Linux (CachyOS) system. The script must:

1. Check if the kernel module amdxdna is loaded using lsmod. If not, print a critical error asking the user to update their kernel to 6.14+.  
2. Check for the existence of firmware files matching 17f0\*.bin in /lib/firmware/amdnpu.  
3. Create a udev rule file at /etc/udev/rules.d/99-uinput.rules that sets KERNEL=="uinput", SUBSYSTEM=="misc", OPTIONS+="static\_node=uinput", TAG+="uaccess" to allow the current user to create virtual input devices without sudo.  
4. Export the environment variable XLNX\_VART\_FIRMWARE pointing to the Strix Halo overlay (search for \*1x4.xclbin in typical installation paths like /opt/xilinx/xrt/share).  
5. Generate a requirements.txt file including numpy, sounddevice, webrtcvad, evdev, scipy, and onnxruntime-gpu (noting in comments that the Vitis-enabled wheel must be installed manually)."

### **8.2 Prompt Set 2: The Virtual Controller Class**

Context: "I need a Python class to emulate an Xbox 360 controller via uinput for Steam compatibility."  
Prompt:  
"Create a Python class VirtualXboxController in src/input\_engine.py using the evdev library.

1. The \_\_init\_\_ method must initialize a uinput.UInput device.  
2. Define the capabilities dictionary (cap) to strictly mimic an Xbox 360 controller:  
   * **Buttons (EV\_KEY):** BTN\_SOUTH (A), BTN\_EAST (B), BTN\_NORTH (X), BTN\_WEST (Y), BTN\_TL (LB), BTN\_TR (RB), BTN\_SELECT (Back), BTN\_START (Start), BTN\_MODE (Guide), BTN\_THUMBL (L3), BTN\_THUMBR (R3).  
   * **Axes (EV\_ABS):** ABS\_X, ABS\_Y (Left Stick), ABS\_RX, ABS\_RY (Right Stick), ABS\_Z, ABS\_RZ (Triggers), ABS\_HAT0X, ABS\_HAT0Y (D-Pad).  
3. **Critical Configuration:** Use evdev.AbsInfo to define the axis ranges. Sticks (X/Y/RX/RY) must have min=-32768, max=32767, fuzz=16, flat=128. Triggers (Z/RZ) must have min=0, max=255.  
4. Set the device vendor to 0x045e and product to 0x028e (Microsoft Xbox 360\) to ensure automatic detection by Steam and Proton.  
5. Implement high-level methods: tap\_button(button\_name), hold\_button(button\_name, duration), and move\_stick(stick\_name, x, y, duration). Use asyncio.sleep for durations."

### **8.3 Prompt Set 3: The NPU Inference Engine**

Context: "I need a wrapper for ONNX Runtime that uses the Vitis AI provider and handles the NPU's static shape requirements."  
Prompt:  
"Create a Python class WhisperNPU in src/inference\_engine.py.

1. The constructor should accept paths to the quantized encoder and decoder ONNX models and a path to vaip\_config.json.  
2. Initialize onnxruntime.InferenceSession for both models. Use the provider list \['VitisAIExecutionProvider', 'CPUExecutionProvider'\]. Pass the config file path in the provider\_options.  
3. Implement a preprocess(audio\_array) method. It must take a raw NumPy audio array and pad or truncate it to exactly 480,000 samples (30 seconds at 16kHz) to satisfy the XDNA compiler's static shape requirement. Use np.pad with mode 'constant'.  
4. Implement a transcribe(audio\_array) method. It should run the encoder session on the preprocessed audio. Then, implement a greedy decoding loop using the decoder session to generate text tokens from the encoder output.  
5. Ensure all input tensors are cast to np.float32 (or the specific type required by the quantized model) and are contiguous in memory using np.ascontiguousarray() to prevent IOMMU faults."

### **8.4 Prompt Set 4: The Async Orchestrator**

Context: "I need to tie the audio capture, VAD, and inference together in a non-blocking loop."  
Prompt:  
"Write the src/main.py script using asyncio.

1. Instantiate VirtualXboxController and WhisperNPU.  
2. Create an asyncio.Queue for audio chunks.  
3. Define a callback function for sounddevice.InputStream that puts incoming audio frames into the queue using call\_soon\_threadsafe.  
4. Create a coroutine process\_audio() that consumes the queue. Use webrtcvad to detect speech. Accumulate audio frames while speech is active.  
5. When silence is detected (end of command), offload the transcriber.transcribe(buffer) call to a thread pool executor using loop.run\_in\_executor to keep the main loop responsive.  
6. Upon receiving the text transcription, match it against a command dictionary (e.g., 'jump' \-\> await controller.tap\_button('BTN\_SOUTH')) and execute the action.  
7. Include a try/finally block to ensure the uinput device is closed properly on exit."

## **9\. Performance Tuning and Troubleshooting**

### **9.1 Latency Optimization**

The primary metric for voice automation is latency.

* **Audio Block Size:** The sounddevice block size determines the interrupt frequency. A size of 1024 or 2048 frames (approx. 60-120ms) offers a balance between low latency and CPU overhead. Smaller blocks may cause buffer underruns on the Python thread.31  
* **NPU Warm-up:** The first inference run on the NPU often incurs a penalty of several seconds as the firmware loads the graph. The application should perform a "dummy" inference with a zero-filled array during the startup phase to ensure the NPU is hot when the user speaks.

### **9.2 Troubleshooting Common Failures**

* **"Device not found" (XRT):** If xrt-smi fails, it often indicates a mismatch between the amdxdna kernel module version and the userspace xrt libraries. Rebuilding the xrt-plugin-amdxdna against the currently running kernel headers usually resolves this.  
* **Controller Not Visible in Steam:** If the virtual controller appears in evtest but not Steam, check the udev permissions. Steam handles input devices directly; if the uinput node lacks the uaccess tag, Steam cannot open it. Additionally, ensure the virtual device is created *before* Steam is launched.

## **10\. Conclusion**

By synthesizing the capabilities of the AMD Strix Halo's XDNA 2 NPU with the flexibility of the Linux uinput subsystem, developers can create a powerful, hands-free automation interface on CachyOS. This architecture leverages the specific strengths of the hardware—high-throughput, low-power inference—while navigating the intricacies of the Arch Linux ecosystem through strategic use of user-space drivers and virtualization. The prompts provided offer a direct path to implementation, abstracting the complexity of hardware interfacing into manageable, generated code modules. This results in a system that is not only functional but optimized for the bleeding edge of AI-integrated mobile computing.

#### **Works cited**

1. Guide to Setting Up AMD Ryzen AI NPU Drivers on Fedora 43 \- DEV Community, accessed on January 3, 2026, [https://dev.to/ankk98/guide-to-setting-up-amd-ryzen-ai-npu-drivers-on-fedora-43-477i](https://dev.to/ankk98/guide-to-setting-up-amd-ryzen-ai-npu-drivers-on-fedora-43-477i)  
2. Inferencing 4 models on AMD NPU and GPU at the same time from a single URL \- Reddit, accessed on January 3, 2026, [https://www.reddit.com/r/LocalLLaMA/comments/1p7e1u9/inferencing\_4\_models\_on\_amd\_npu\_and\_gpu\_at\_the/](https://www.reddit.com/r/LocalLLaMA/comments/1p7e1u9/inferencing_4_models_on_amd_npu_and_gpu_at_the/)  
3. Increase llama.cpp performance \- strategies for AMD Ryzen AI Max 395+ · Issue \#5 · geerlingguy/beowulf-ai-cluster \- GitHub, accessed on January 3, 2026, [https://github.com/geerlingguy/beowulf-ai-cluster/issues/5](https://github.com/geerlingguy/beowulf-ai-cluster/issues/5)  
4. AMD Ryzen™ AI Software, accessed on January 3, 2026, [https://www.amd.com/en/developer/resources/ryzen-ai-software.html](https://www.amd.com/en/developer/resources/ryzen-ai-software.html)  
5. Unlocking On Device ASR with Whisper on Ryzen AI NPUs \- AMD, accessed on January 3, 2026, [https://www.amd.com/en/developer/resources/technical-articles/2025/unlocking-on-device-asr-with-whisper-on-ryzen-ai-npus.html](https://www.amd.com/en/developer/resources/technical-articles/2025/unlocking-on-device-asr-with-whisper-on-ryzen-ai-npus.html)  
6. Running whisper-large-v3-turbo (OpenAI) Exclusively on AMD Ryzen™ AI NPU \- Reddit, accessed on January 3, 2026, [https://www.reddit.com/r/LocalLLaMA/comments/1odavba/running\_whisperlargev3turbo\_openai\_exclusively\_on/](https://www.reddit.com/r/LocalLLaMA/comments/1odavba/running_whisperlargev3turbo_openai_exclusively_on/)  
7. Linux 7.0 To Remove Support For AMD's Never-Released Ryzen AI NPU2 \- Phoronix, accessed on January 3, 2026, [https://www.phoronix.com/news/Linux-Dropping-AMD-NPU2](https://www.phoronix.com/news/Linux-Dropping-AMD-NPU2)  
8. AMD XDNA Linux Driver Preps For New Ryzen AI "NPU3A" Revision \- Phoronix, accessed on January 3, 2026, [https://www.phoronix.com/news/AMD-Ryzen-AI-XDNA-NPU3A](https://www.phoronix.com/news/AMD-Ryzen-AI-XDNA-NPU3A)  
9. amd/xdna-driver \- GitHub, accessed on January 3, 2026, [https://github.com/amd/xdna-driver](https://github.com/amd/xdna-driver)  
10. Optimized Repositories \- the CachyOS Wiki, accessed on January 3, 2026, [https://wiki.cachyos.org/features/optimized\_repos/](https://wiki.cachyos.org/features/optimized_repos/)  
11. CachyOS May 2024 Release, accessed on January 3, 2026, [https://cachyos.org/blog/2405-may-release/](https://cachyos.org/blog/2405-may-release/)  
12. General System Tweaks \- the CachyOS Wiki, accessed on January 3, 2026, [https://wiki.cachyos.org/configuration/general\_system\_tweaks/](https://wiki.cachyos.org/configuration/general_system_tweaks/)  
13. Linux Installation Instructions — Ryzen AI Software 1.6.1 documentation, accessed on January 3, 2026, [https://ryzenai.docs.amd.com/en/latest/linux.html](https://ryzenai.docs.amd.com/en/latest/linux.html)  
14. GUI Installer \- the CachyOS Wiki, accessed on January 3, 2026, [https://wiki.cachyos.org/cachyos\_basic/changelogs/gui\_installer/](https://wiki.cachyos.org/cachyos_basic/changelogs/gui_installer/)  
15. Gaming with CachyOS Guide, accessed on January 3, 2026, [https://wiki.cachyos.org/configuration/gaming/](https://wiki.cachyos.org/configuration/gaming/)  
16. Xorg input driver \- the easy way, via evdev and uinput \- My blog\_title\_here, accessed on January 3, 2026, [https://blog.fraggod.net/2017/02/13/xorg-input-driver-the-easy-way-via-evdev-and-uinput.html](https://blog.fraggod.net/2017/02/13/xorg-input-driver-the-easy-way-via-evdev-and-uinput.html)  
17. python-uinput \- PyPI, accessed on January 3, 2026, [https://pypi.org/project/python-uinput/](https://pypi.org/project/python-uinput/)  
18. Status of AMD NPU Support \- Linux \- Framework Community, accessed on January 3, 2026, [https://community.frame.work/t/status-of-amd-npu-support/65191](https://community.frame.work/t/status-of-amd-npu-support/65191)  
19. \[Package Request\] AMD NPU / Ryzen AI Userspace Stack \- Arch Linux Forums, accessed on January 3, 2026, [https://bbs.archlinux.org/viewtopic.php?id=304979](https://bbs.archlinux.org/viewtopic.php?id=304979)  
20. \[Package Request\] AMD NPU / Ryzen AI Userspace Stack \- Repository \- CachyOS Forum, accessed on January 3, 2026, [https://discuss.cachyos.org/t/package-request-amd-npu-ryzen-ai-userspace-stack/8036](https://discuss.cachyos.org/t/package-request-amd-npu-ryzen-ai-userspace-stack/8036)  
21. AMD NPU Firmware Upstreamed For The Ryzen AI AMDXDNA Driver Coming In Linux 6.14, accessed on January 3, 2026, [https://www.phoronix.com/forums/forum/linux-graphics-x-org-drivers/open-source-amd-linux/1509807-amd-npu-firmware-upstreamed-for-the-ryzen-ai-amdxdna-driver-coming-in-linux-6-14](https://www.phoronix.com/forums/forum/linux-graphics-x-org-drivers/open-source-amd-linux/1509807-amd-npu-firmware-upstreamed-for-the-ryzen-ai-amdxdna-driver-coming-in-linux-6-14)  
22. Linux Setup and Build Instructions | Xilinx AIEngine MLIR Dialect, accessed on January 3, 2026, [https://xilinx.github.io/mlir-aie/buildHostLin.html](https://xilinx.github.io/mlir-aie/buildHostLin.html)  
23. AMD \- Vitis AI | onnxruntime \- GitHub Pages, accessed on January 3, 2026, [https://fs-eire.github.io/onnxruntime/docs/execution-providers/Vitis-AI-ExecutionProvider.html](https://fs-eire.github.io/onnxruntime/docs/execution-providers/Vitis-AI-ExecutionProvider.html)  
24. How to inference using NPU with onnxruntime on Linux · Issue \#178 · amd/RyzenAI-SW, accessed on January 3, 2026, [https://github.com/amd/RyzenAI-SW/issues/178](https://github.com/amd/RyzenAI-SW/issues/178)  
25. Model Compilation and Deployment — Ryzen AI Software 1.4 documentation, accessed on January 3, 2026, [https://ryzenai.docs.amd.com/en/1.4/modelrun.html](https://ryzenai.docs.amd.com/en/1.4/modelrun.html)  
26. ONNX | PySDK \- DeGirum Docs, accessed on January 3, 2026, [https://docs.degirum.com/pysdk/runtimes-and-drivers/onnx-runtime](https://docs.degirum.com/pysdk/runtimes-and-drivers/onnx-runtime)  
27. amd/NPU-Whisper-Base-Small \- Hugging Face, accessed on January 3, 2026, [https://huggingface.co/amd/NPU-Whisper-Base-Small](https://huggingface.co/amd/NPU-Whisper-Base-Small)  
28. Run Machine Learning Inference on the NPU with PyTorch and ONNX — Riallto \- An exploration framework for Ryzen AI, accessed on January 3, 2026, [https://riallto.ai/notebooks/5\_1\_pytorch\_onnx\_inference.html](https://riallto.ai/notebooks/5_1_pytorch_onnx_inference.html)  
29. How to calibrate joystick using evdev-joystick? : r/linux\_gaming \- Reddit, accessed on January 3, 2026, [https://www.reddit.com/r/linux\_gaming/comments/anb3ij/how\_to\_calibrate\_joystick\_using\_evdevjoystick/](https://www.reddit.com/r/linux_gaming/comments/anb3ij/how_to_calibrate_joystick_using_evdevjoystick/)  
30. How to access the joysticks of a gamepad using python evdev? \- Stack Overflow, accessed on January 3, 2026, [https://stackoverflow.com/questions/44934309/how-to-access-the-joysticks-of-a-gamepad-using-python-evdev](https://stackoverflow.com/questions/44934309/how-to-access-the-joysticks-of-a-gamepad-using-python-evdev)  
31. python-sounddevice/examples/asyncio\_generators.py at master \- GitHub, accessed on January 3, 2026, [https://github.com/spatialaudio/python-sounddevice/blob/master/examples/asyncio\_generators.py](https://github.com/spatialaudio/python-sounddevice/blob/master/examples/asyncio_generators.py)  
32. Asyncio concepts and design patterns | by Kanak Singh \- Medium, accessed on January 3, 2026, [https://medium.com/@Singh314/asyncio-concepts-and-design-patterns-6cee5b7ba504](https://medium.com/@Singh314/asyncio-concepts-and-design-patterns-6cee5b7ba504)