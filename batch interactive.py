from os import path, system, mkdir
import sys
from multiprocessing import Pool
import subprocess
from glob import glob
from PIL import Image, ImageFont, ImageDraw
from svglib import svglib
import textwrap

vinyl_path = path.abspath('./x64/Release/vinyl.exe')
ffmpeg_path = path.abspath('./ffmpeg.exe')
inkscape_path = path.abspath('../inkscape/inkscape.exe')

dimensions = 4000
font = 'playtime.ttf'
title_height = 576
title_pt = 512
title_outline = 32
subtitle_pt = 256
subtitle_outline = 16
padding = 128

def downsize(job):    
    cmd = '"{ffmpeg}" -i "{i}" -vf scale=-1:144 "{o}"'.format(ffmpeg=ffmpeg_path, i=job['original_path'], o=job['video_path'])
    p = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
    p.communicate()
    print('#{id} {name} now smol'.format(id=job['id'], name=path.basename(job['original_path'])))

def generate_svg(job):
    if path.isfile(job['svg_path']):
        print('#{id} {name} skipped'.format(id=job['id'], name=path.basename(job['original_path'])))
        sys.stdout.flush()
    else:
        cmd = '"{vinyl}" "{file}" --scale=4 -r 10 -p'.format(
            vinyl=vinyl_path,
            file=job['original_path']
            )
    
        p = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        p.communicate()
        print('#{id} {name} finished'.format(id=job['id'], name=path.basename(job['original_path'])))
        sys.stdout.flush()
    
def render_png(job):
    if path.isfile(job['png_path']):
        print('#{id} {name} skipped'.format(id=job['id'], name=path.basename(job['svg_path'])))
        sys.stdout.flush()
    else:
        cmd = '"{inkscape}" --file="{svg}" --without-gui --export-png="{png}" --export-height={height}'.format(
            inkscape=inkscape_path,
            svg=job['svg_path'],
            png=job['png_path'],
            height=dimensions
            )
    
        p = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        p.communicate()
        print('#{id} {name} finished'.format(id=job['id'], name=path.basename(job['svg_path'])))
        sys.stdout.flush()

if __name__ == '__main__':
    if len(sys.argv) < 2 or not path.isdir(sys.argv[1]):
        print('No valid directory provided. Using ./')
        dir = path.abspath('.')
    else:
        dir = path.abspath(sys.argv[1])
        
    #wdir = path.join(dir, 'wdir')
    #if not path.exists(wdir): mkdir(wdir)

    video_paths = []
    for f in ['mkv']: video_paths.extend(glob(path.join(dir, '*.' + f)))
    print('{n} video files found in {path}'.format(n=len(video_paths), path=dir))
    
    title = input('Choose title: ')
    prefix = input('Choose prefix: ')
    rowlimit = [ int(n) for n in input('Row limit: ').split() if n.isnumeric() ]
    if sum(rowlimit) > len(video_paths):
        print('too many.')
        exit(0)
    if sum(rowlimit) < len(video_paths):
        print('append list with {item}'.format(item=(len(video_paths) - sum(rowlimit))))
        rowlimit.append(len(video_paths) - sum(rowlimit))

    jobs = []
    subtitle_height = 0
    for i, p in enumerate(video_paths):
        prefix_i = prefix.replace('{n}', str(i+1))
        title_i = (prefix_i + textwrap.fill(input('Title for {name}: {prefix}'.format(prefix=prefix_i, name=path.basename(p))), 32)).replace('>', '\n')
        subtitle_height = max(subtitle_height, (title_i.count('\n') + 2) * subtitle_pt)
        jobs.append(
            {
                'id' : i,
                'original_path': p,
                'video_path': path.join(dir, path.splitext(path.basename(p))[0] + '.mp4'),
                'svg_path': path.join(dir, path.splitext(path.basename(p))[0] + '.svg'),
                'png_path': path.join(dir, path.splitext(path.basename(p))[0] + '.png'),
                'title': title_i
                })
    #print('\n'.join([ str(job) for job in jobs ]))

    pool = Pool(8)
    
    #print('Downsizing video')
    #sys.stdout.flush()
    #pool.map(downsize, jobs)
    #print('All videos are smol')

    print('Generating vinyl svgs')
    sys.stdout.flush()
    pool.map(generate_svg, jobs)
    print('All vinyl svgs finished')
    
    print('Rendering pngs')
    sys.stdout.flush()
    pool.map(render_png, jobs)
    print('All pngs finished')
    sys.stdout.flush()

    pool.close()
    pool.join()

    canvas = Image.new(
        mode='RGBA',
        size=(
            max(rowlimit) * (dimensions + padding) + padding,
            len(rowlimit) * (dimensions + (subtitle_height if any([ i['title'] for i in jobs ]) else 0) + padding) + (title_height + padding if title else 0) + padding
            ),
        color=(255, 255, 255, 0)
        )
    draw = ImageDraw.Draw(canvas)

    title_font = ImageFont.truetype(font, title_pt)
    subtitle_font = ImageFont.truetype(font, subtitle_pt)

    if title:
        w, h = draw.textsize(title, title_font)
        draw.text(
            (
                ((max(rowlimit) * dimensions + (max(rowlimit) - 1) * padding) / 2) - (w / 2) + padding,
                (title_height / 2) - (h / 2) + padding
                ),
                title,
                fill=(255, 255, 255),
                font=title_font,
                stroke_width=title_outline,
                stroke_fill=(20, 20, 20)
            )


    for r, limit in enumerate(rowlimit):
        offset_y = int(padding + (title_height + padding if title else 0) + r * (dimensions + (subtitle_height if any([ i['title'] for i in jobs ]) else 0) + padding))

        for c in range(limit):
            i = sum(rowlimit[:r]) + c
            offset_x = int(((dimensions + padding) * (max(rowlimit) - limit) / 2) + ((dimensions + padding) * c) + padding)

            canvas.paste(
                Image.open(jobs[i]['png_path']),
                (offset_x, offset_y)
                )

            w, h = draw.multiline_textsize(jobs[i]['title'], subtitle_font)
            draw.multiline_text(
                (
                    offset_x + (dimensions / 2) - (w / 2),
                    offset_y + dimensions + (subtitle_pt / 2)
                    ),
                    jobs[i]['title'],
                    fill=(255, 255, 255),
                    font=subtitle_font,
                    stroke_width=subtitle_outline,
                    stroke_fill=(20, 20, 20),
                    align='center'
                )

    canvas.save(path.join(dir, 'vinyl.png'))
    
