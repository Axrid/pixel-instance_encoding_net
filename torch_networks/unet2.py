import torch
import torch.nn.functional as F
from torch import nn
from utils import initialize_weights
from deformConv2D import Conv2dDeformable

class _EncoderBlock(nn.Module):
    def __init__(self, in_channels, out_channels, deformConv=False, dropout=False):
        super(_EncoderBlock, self).__init__()
        layers = [
            nn.Conv2d(in_channels, out_channels, kernel_size=3),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        ]

        if deformConv:
            layers[0] = Conv2dDeformable(layers[0])
            layers[3] = Conv2dDeformable(layers[3])
        if dropout:
            layers.append(nn.Dropout())
        layers.append(nn.MaxPool2d(kernel_size=2, stride=2))
        self.encode = nn.Sequential(*layers)

    def forward(self, x):
        return self.encode(x)


class _DecoderBlock(nn.Module):
    def __init__(self, in_channels, middle_channels, out_channels,deformConv=False):
        super(_DecoderBlock, self).__init__()
        layers = [
            nn.Conv2d(in_channels, middle_channels, kernel_size=3),
            nn.BatchNorm2d(middle_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(middle_channels, middle_channels, kernel_size=3),
            nn.BatchNorm2d(middle_channels),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(middle_channels, out_channels, kernel_size=2, stride=2),
        ]
        if deformConv:
           layers[0] = Conv2dDeformable(layers[0])
           layers[3] = Conv2dDeformable(layers[3])

        self.decode = nn.Sequential(*layers)

    def forward(self, x):
        return self.decode(x)


class UNet(nn.Module):
    def __init__(self, num_classes, deformConv = False):
        super(UNet, self).__init__()
        self.deformConv = deformConv
        self.enc1 = _EncoderBlock(1, 64,deformConv)
        self.enc2 = _EncoderBlock(64, 128,deformConv)
        self.enc3 = _EncoderBlock(128, 256,deformConv)
        self.enc4 = _EncoderBlock(256, 512, dropout=True,deformConv=deformConv)
        self.center = _DecoderBlock(512, 1024, 512,deformConv)
        self.dec4 = _DecoderBlock(1024, 512, 256,deformConv)
        self.dec3 = _DecoderBlock(512, 256, 128,deformConv)
        self.dec2 = _DecoderBlock(256, 128, 64,deformConv)
        dec1_layers = [
            nn.Conv2d(128, 64, kernel_size=3),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, kernel_size=3),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
        ]

        if deformConv:
            layers[0] = Conv2dDeformable(layers[0])
            layers[3] = Conv2dDeformable(layers[3])

        self.dec1 = nn.Sequential(*dec1_layers)
        self.final = nn.Conv2d(64, num_classes, kernel_size=1)
        initialize_weights(self)

    def forward(self, x):
        enc1 = self.enc1(x)
        enc2 = self.enc2(enc1)
        enc3 = self.enc3(enc2)
        enc4 = self.enc4(enc3)
        center = self.center(enc4)
        dec4 = self.dec4(torch.cat([center, F.upsample(enc4, center.size()[2:], mode='bilinear')], 1))
        dec3 = self.dec3(torch.cat([dec4, F.upsample(enc3, dec4.size()[2:], mode='bilinear')], 1))
        dec2 = self.dec2(torch.cat([dec3, F.upsample(enc2, dec3.size()[2:], mode='bilinear')], 1))
        dec1 = self.dec1(torch.cat([dec2, F.upsample(enc1, dec2.size()[2:], mode='bilinear')], 1))
        final = self.final(dec1)
        return F.upsample(final, x.size()[2:], mode='bilinear')
    @property
    def name(self):
        return 'Unet_II_DeformConv' if self.deformConv else 'Unet_II'