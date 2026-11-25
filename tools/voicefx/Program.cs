// 목소리 변조 도구 (NAudio.Core): 녹음을 '메가폰에서 나오는 소녀 목소리'로 바꿔 게임 목소리 폴더에 넣는다.
//
// 사용: tools/dotnet.sh run --project tools/voicefx -- <입력.wav> <출력.wav> [--pitch 1.75] [--start 초] [--no-megaphone]
//   입력: WAV. macOS에서는 m4a·mp3 등도 그대로 넣으면 afconvert 로 자동 변환한다.
//   --pitch: 음높이 배율 (1.0=그대로, 2.0=한 옥타브 위). 말 빠르기는 바뀌지 않는다.
//   --start: 입력에서 이 시각(초) 이전을 버린다 — 말 앞의 들숨·잡음 제거용. 메가폰의 찌그러뜨림이
//            작은 숨소리도 키우기 때문에 게임의 자동 무음 제거만으로는 들숨이 남는다.
using NAudio.Dsp;
using NAudio.Wave;
using NAudio.Wave.SampleProviders;

if (args.Length < 2)
{
    Console.Error.WriteLine("사용: VoiceFx <녹음 파일> <voices/이름/chant.wav> [--pitch 1.75] [--start 초] [--no-megaphone]");
    return 1;
}
string input = args[0], output = args[1];
float pitch = 1.75f;
double start = 0;
bool megaphone = true;
for (int i = 2; i < args.Length; i++)
{
    if (args[i] == "--pitch" && i + 1 < args.Length) pitch = float.Parse(args[++i], System.Globalization.CultureInfo.InvariantCulture);
    else if (args[i] == "--start" && i + 1 < args.Length) start = double.Parse(args[++i], System.Globalization.CultureInfo.InvariantCulture);
    else if (args[i] == "--no-megaphone") megaphone = false;
}

if (!File.Exists(input))
{
    Console.Error.WriteLine($"입력 파일이 없습니다: {Path.GetFullPath(input)}");
    Console.Error.WriteLine("녹음 파일의 실제 경로를 넣어 주세요. 예: ~/Downloads/내녹음.m4a");
    return 1;
}

// WAV가 아니면(m4a, mp3 등) macOS 기본 도구 afconvert 로 임시 WAV를 만든다
string? tempWav = null;
if (!input.EndsWith(".wav", StringComparison.OrdinalIgnoreCase))
{
    if (!OperatingSystem.IsMacOS())
    {
        Console.Error.WriteLine("WAV 파일만 넣을 수 있습니다. 녹음 앱이나 변환 프로그램으로 WAV로 바꿔 주세요.");
        return 1;
    }
    tempWav = Path.Combine(Path.GetTempPath(), $"voicefx-{Guid.NewGuid():N}.wav");
    var psi = new System.Diagnostics.ProcessStartInfo("afconvert") { RedirectStandardError = true };
    foreach (var a in new[] { "-f", "WAVE", "-d", "LEI16@44100", "-c", "1", input, tempWav }) psi.ArgumentList.Add(a);
    using var proc = System.Diagnostics.Process.Start(psi)!;
    proc.WaitForExit();
    if (proc.ExitCode != 0)
    {
        Console.Error.WriteLine($"WAV로 바꾸지 못했습니다: {proc.StandardError.ReadToEnd().Trim()}");
        return 1;
    }
    input = tempWav;
}

using var reader = new WaveFileReader(input);
int sr = reader.WaveFormat.SampleRate;
ISampleProvider source = reader.ToSampleProvider();
if (source.WaveFormat.Channels == 2) source = new StereoToMonoSampleProvider(source);
if (start > 0) source = new OffsetSampleProvider(source) { SkipOver = TimeSpan.FromSeconds(start) };

// 1) 음높이 올리기 (속도 유지)
var shifted = new SmbPitchShiftingSampleProvider(source, 4096, 8L, pitch);
var samples = new List<float>();
var buf = new float[sr];
int n;
while ((n = shifted.Read(buf.AsSpan())) > 0) samples.AddRange(buf.AsSpan(0, n).ToArray());

// 잘라낸 지점에서 '툭' 소리가 나지 않게 앞 15ms를 서서히 키운다
int fade = Math.Min(samples.Count, (int)(sr * 0.015));
for (int i = 0; i < fade; i++) samples[i] *= i / (float)fade;

// 울림이 끝까지 들리도록 뒤에 여유를 둔다
samples.AddRange(new float[(int)(sr * 0.8)]);
float[] x = samples.ToArray();

if (megaphone)
{
    // 2) 메가폰 음색: 저음·고음을 잘라 좁은 대역만 남기고, 중음(코맹맹이 소리)을 키운다
    var filters = new[]
    {
        BiQuadFilter.HighPassFilter(sr, 550, 0.9f),
        BiQuadFilter.HighPassFilter(sr, 550, 0.9f),
        BiQuadFilter.LowPassFilter(sr, 3600, 0.9f),
        BiQuadFilter.LowPassFilter(sr, 3600, 0.9f),
        BiQuadFilter.PeakingEQ(sr, 1700, 1.4f, 8f),
    };
    for (int i = 0; i < x.Length; i++)
        foreach (var f in filters) x[i] = f.Transform(x[i]);

    // 3) 싸구려 스피커처럼 살짝 찌그러뜨린다 (부드러운 클리핑)
    Normalize(x, 0.9f);
    const float drive = 3.0f;
    float norm = MathF.Tanh(drive);
    for (int i = 0; i < x.Length; i++) x[i] = MathF.Tanh(x[i] * drive) / norm;

    // 4) 나팔관 공명: 아주 짧은 지연을 되먹여 금속성 울림을 만든다
    int horn = (int)(sr * 0.0011);
    for (int i = horn; i < x.Length; i++) x[i] += 0.35f * x[i - horn];

    // 5) 넓은 공간에 울려 퍼지는 메아리
    var y = (float[])x.Clone();
    foreach (var (delay, gain) in new[] { (0.11, 0.30f), (0.23, 0.18f), (0.37, 0.10f), (0.55, 0.05f) })
    {
        int d = (int)(sr * delay);
        for (int i = d; i < y.Length; i++) y[i] += gain * x[i - d];
    }
    x = y;
}

Normalize(x, 0.9f);
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
using (var writer = new WaveFileWriter(output, new WaveFormat(sr, 16, 1)))
    writer.WriteSamples(x, 0, x.Length);
reader.Dispose();
if (tempWav != null) File.Delete(tempWav);
Console.WriteLine($"완료: {output} ({x.Length / (double)sr:F2}초, 시작 {start}초부터, 음높이 x{pitch}, 메가폰 {(megaphone ? "켬" : "끔")})");
return 0;

static void Normalize(float[] x, float peak)
{
    float max = 0;
    foreach (var v in x) max = MathF.Max(max, MathF.Abs(v));
    if (max <= 0) return;
    float k = peak / max;
    for (int i = 0; i < x.Length; i++) x[i] *= k;
}
